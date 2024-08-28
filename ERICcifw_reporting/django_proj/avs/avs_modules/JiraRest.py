import urllib2, base64
import json
import logging

logger = logging.getLogger(__name__)

class JiraRest:
    """Python class to make REST call to JIRA

    Takes in a JIRA issue id (as a string) and returns a json object
    """

    def jiraRestCall(self, jiraIssueId):
        """Method to make a REST call to JIRA

        Takes in:   JIRA issue as a string
        Returns:    A json object representation of the JIRA response
        """
        requestAddress = 'http://jira-oss.seli.wh.rnd.internal.ericsson.com/rest/api/latest/issue/' + jiraIssueId
        request = urllib2.Request(requestAddress)
        #TODO: need to read in user & pass from new config files set up by CJ
        base64string = base64.encodestring('%s:%s' % ('lciadm100', 'lciadm100')).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        try:
            jiraResponse = urllib2.urlopen(request).read()
            jsonResponse = json.loads(jiraResponse)
            return jsonResponse
        except Exception, error:
            logger.info("Exception: %s", error)
            if error.code == 403:
                jsonResponse = {'errorMessage': 'lciadm100 User does not have access to JIRA Project' }
            else:
                jsonResponse = {'errorMessage': '%s User story does not exist in JIRA' %jiraIssueId }
            return jsonResponse
        return ""

    def getJiraIdDetails(self, jiraIssueId):
        """Method return the details for the gieven JIRA issue id
        
        Takes in: JIRA issue as a string
        Returns: A dictionary containing the type, title & parent for the suppplied JIRA issue     
        """
        logger.info("Looking up UserStoryId: %s" % jiraIssueId)
        jsonResponse = self.jiraRestCall(jiraIssueId)
        if 'errorMessage' in jsonResponse.keys():
            logger.debug('Error occurred in JIRA lookup \n JIRA response: \n %s' %jsonResponse)
            response = jsonResponse
        else:
            jiraIssueIdType = jsonResponse['fields']['issuetype']['name']
            jiraIssueIdTitle = jsonResponse['fields']['summary']  
            try:
                jiraIssueIdParent = jsonResponse['fields']['customfield_12600']
                if jiraIssueIdParent is None:
                    logger.debug("Epic not found under Epic-Link, will try Epic-Theme")
                    jiraIssueIdParent = jsonResponse['fields']['customfield_10121'][0]
                    if jiraIssueIdParent is not None:
                        logger.debug("Found Epic under 'Epic-Theme': %s" %jiraIssueIdParent)
                    else:  
                        logger.debug("User Story has no Epic in JIRA")
            except Exception, error:
                logger.debug("An error occurred when lookig up the Epic for this userstory",error)
                jiraIssueIdParent = None
            
            logger.debug('JIRA Issue ID Type: %s, JIRA Issue ID Title: %s, JIRA Issue ID Parent: %s' %(jiraIssueIdType,jiraIssueIdTitle,jiraIssueIdParent))
            response = {"jiraIssueId": jiraIssueId, "jiraIssueIdType":jiraIssueIdType, "jiraIssueIdTitle":jiraIssueIdTitle, "jiraIssueIdParent":jiraIssueIdParent}        
            logger.debug('Sucessfully finished looking up UserStoryId: %s' % jiraIssueId)
        return response

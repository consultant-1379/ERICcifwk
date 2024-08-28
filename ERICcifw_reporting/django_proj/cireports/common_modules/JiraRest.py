import urllib2, base64
import json
import logging
from ciconfig import CIConfig

logger = logging.getLogger(__name__)

class Ddict(dict):
    def __init__(self, default=None):
        self.default = default

    def __getitem__(self, key):
        if not self.has_key(key):
            self[key] = self.default()
        return dict.__getitem__(self, key)

class JiraRest:
    """Python class to make REST call to JIRA

    Takes in a JIRA jql statement (as a string) and returns a json object
    """

    def jiraRestCallSearch(self, jql):
        """Method to make a REST call to JIRA

        Takes in:   jql statement as a string
        Returns:    A json object representation of the JIRA response
        """
        #Get jira username /password from config file
        config = CIConfig()
        jiraUser = config.get("CIFWK", "jiraUser")
        jiraPassword = config.get("CIFWK", "jiraPassword")
        jqlNew = jql.replace(' ','%20')
        jqlNew = jql.replace('"','%22')
        requestAddress = 'http://jira-oss.seli.wh.rnd.internal.ericsson.com//rest/api/2/search?jql=' + jqlNew + '&maxResults=10000'
        try:
            request = urllib2.Request(requestAddress)
        except Exception as e:
            logger.warning("There was an issue with finding DropName and CXP given in Jira:" +str(e))
        base64string = base64.encodestring('%s:%s' % (jiraUser, jiraPassword)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        try:
            jiraResponse = urllib2.urlopen(request).read()
            jsonResponse = json.loads(jiraResponse)
            return jsonResponse

        except Exception, error:
            if error.code == 403:
                jsonResponse = {'errorMessage': 'lciadm100 User does not have access to JIRA Project' }
            else:
                jsonResponse = {'errorMessage': '%s Invalid search string ' %jql }
            return jsonResponse
        return ""


    def getJiraIdDetails(self, jql, fieldsToGet):
        """Method return the details for the gieven JIRA issue id
        
        Takes in:  jql statement as a string and fields to return
        Returns: An indexed dictionary containing value<x> and the field requested      
        """
        logger.debug("Jira lookup: %s" % jql)
        jsonResponse = self.jiraRestCallSearch(jql)
        if 'errorMessage' in jsonResponse.keys():
            logger.debug('Issue occurred in JIRA lookup \n JIRA response: \n %s' %jsonResponse)
            ret = 'null' 
        else:
            for mainfield in jsonResponse:
                mainfield1 =mainfield
                break
            jsonResponseFields = jsonResponse[mainfield1]
            ret = Ddict( dict )
            retid = 0 
            if jsonResponseFields == 0:
                return 'null'
            for issuex in jsonResponseFields:
                valueCount=0
                for field in fieldsToGet:
                    tempRes = issuex
                    for subField in field:
                        try:
                            tempRes = tempRes[subField]
                        except Exception, error:
                            tempRes='null'
                    tmpValue="value"+str(valueCount)
                    valueCount +=1
                    ret[retid][tmpValue] = tempRes 
                retid += 1
        return ret

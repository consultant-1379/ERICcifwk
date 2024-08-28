from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode
import logging
logger = logging.getLogger(__name__)

def logAction(userId, object, action, message, dictDeletedInfo=None):
    '''
    Function to add the user activity on the portal and log in the admin log entry db
    Inputs are:
        userId:             The id of the current user log in
        object:             To log the data against
        action:             The action perfromed i.e. add, edit, delete
        message:            The message to be attached this message should be in certain format to it can be parsed and displayed again
        dictDeletedInfo:    This is used in a delete, as the object that it needs would have been
                            deleted at this point, so it needs to set the info as a list before the deletion
                            Three items in the dict
                                contentTypeId
                                objectId
                                objectRep
    Output:
        User Activity logged in the django_admin_log table in the database
    '''

    if action.lower() == "add":
        actionFlag = 1
    elif action.lower() == "edit":
        actionFlag = 2
    elif action.lower() == "delete":
        actionFlag = 3

    try:
        if dictDeletedInfo != None:
            contentTypeId = dictDeletedInfo['contentTypeId']
            objectId = dictDeletedInfo['objectId']
            objectRep = dictDeletedInfo['objectRep']
        else:
            contentTypeId = ContentType.objects.get_for_model(object).pk
            objectId = object.pk
            objectRep = force_unicode(object)
        LogEntry.objects.log_action(userId, contentTypeId, objectId, objectRep, actionFlag, message)
    except Exception as e:
        logger.error("There was an issue storing information for an adding or edit into the Django Admin Logger, Exception : " + str(e))

def logChange(oldValues,newValues):
    '''
    Function used to search through the old values and new values and list back the changes for logging purposes
    Inputs:
        oldValues:  A list of the old values given into the edit form
        newValues:  A list of the new values got back from the post of the form
    Output:
        changedContent: A String of the Changes
    '''
    # Create a dictionary of the two lists
    oldNewDict = dict(zip(oldValues, newValues))
    changedContent = ""
    for key, newValue in oldNewDict.iteritems():
        # Split the key to get the comment
        oldValue = key.split("##")[0]
        oldValueComment = key.split("##")[1]
        if oldValue == "None":
            oldValue = ""
        if newValue == "None":
            newValue = ""
        if oldValue != newValue:
            changedContent+= str(oldValueComment) + " was \"" + str(oldValue) + "\" now \"" + str(newValue) + "\" "
    if changedContent == "":
       changedContent = "No Changes Made"
    return changedContent

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
import time, logging, paramiko

logger = logging.getLogger(__name__)

def sftp(node, port, user, password, remotefile, localfile, type):
    logger.info("Attempting to set up the SFTP Transport Connection")
    try:
        transport = paramiko.Transport((node, port))
        logger.info("SFTP Transport Connection opened on Node: " +str(node)+ 
                " Port Number: " + str(port))
    except Exception as e:
        logger.error("SFTP  transport connection unable to open on Node : " + str(node) +
                " Port Number: " + str(port) + " Error Thrown: " + str(e))
        return False


    # Auth
    logger.info("Attempting to authenticated the SFTP transport connection")
    try:
        transport.connect(username = user, password = password)
        logger.info("Authenticated the SFTP transport connection Successful")
    except Exception as e:
        logger.error("Authenticated of the SFTP transport connection Failed with Error: " 
                + str(e))
        return False

    # Go!
    logger.info("Attempting to create the sftp connection")
    try:
        sftp = paramiko.SFTPClient.from_transport(transport)
        logger.info("SFTP Connection Successful")
    except Exception as e:
        logger.error("SFTP Connection UNSuccessful Error thrown: "
                + str(e))
        return False
    if type == "get":
        # Download
        logger.info("Downloading file from: " + remotefile + " to " + localfile)
        try:
            sftp.get(remotefile, localfile)
            logger.info("Download was a success")
        except Exception as e:
            logger.error("Download was not a success, error thrown: " + str(e))
            return False
    elif type == "put":
        # Upload
        logger.info("Uploading file from:" + remotefile + " to " + localfile) 
        try:
            sftp.put(remotefile, localfile)
            logger.info("Uploading was a success")
        except Exception as e:
            logger.error("Uploading was a Failure, Error was thrown: " + str(e))
            return False

    # Close
    time.sleep(5)
    logger.info("Closing SFTP connection")
    try:
        sftp.close()
        logger.info("Successfully Closed SFTP Connection")
    except Exception as e:
        logger.error("Unable to close SFTP Connection Error Thrown: " +str(e))
        return False
    logger.info("Attempting to close the SFTP Transport Connection")
    try:
        transport.close()
        logger.info("SFTP Transport Connection closed with Success")
    except Exception as e:
        logger.error("SFTP Transport Connection could not be closed, Error Thrown: " +str(e))
        return False

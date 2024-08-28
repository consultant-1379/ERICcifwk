'''monitorLocalDiskUsage'''
import sys,os,statvfs,socket,logging,subprocess
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from ciconfig import CIConfig
config = CIConfig()

logger = logging.getLogger(__name__)

def usedSpace(filesystemItem):
    '''
    The purpose of the usedSpace def is to determine the amount of
    in percentage of how much used space there is on a given
    filesystem weather attached or mounted
    '''
    try:
        filesystem = os.statvfs(filesystemItem)
        logger.info("FILE SYSTEM NOW MONITORING: " +str(filesystemItem)+ "\n")
        logger.info("BLOCK INFOMATION\n")
        blockSize = filesystem[statvfs.F_BSIZE]
        logger.info("BLOCK SIZE: " + str(blockSize) +  " BYTES")
        totalBlocks = filesystem[statvfs.F_BLOCKS]
        logger.info("Total Blocks: " + str(totalBlocks) + " BLOCKS")
        availableBlocks = filesystem[statvfs.F_BAVAIL]
        logger.info("Available Blocks: " + str(availableBlocks) + " BLOCKS")
        usedBlocks = filesystem[statvfs.F_BLOCKS] - filesystem[statvfs.F_BAVAIL]
        logger.info("Used Blocks: " + str(usedBlocks) + " BLOCKS\n")
        logger.info("DISK INFOMATION\n")
        totalDisk = (totalBlocks * blockSize)
        logger.info("Total Disk Size: " +str(totalDisk)+ " Bytes")
        usedDisk = (usedBlocks * blockSize)
        logger.info("Used Disk: " +str(usedDisk)+ " Bytes")
        freeDisk = (totalDisk - usedDisk)
        logger.info("Free Disk: " + str(freeDisk)+ " Bytes\n")


    except Exception as e:
        logger.warning("There was an issue gathering disk information on Disk : '"
                        + str(filesystemItem) + "' Error: "  + str(e))
        return False
    try:
        percentageUsedBlocks = (float(usedBlocks) / float(totalBlocks)) * 100 
        logger.info("PERCENTAGE BLOCKS USED: " + str(float(percentageUsedBlocks)) + "%")
        percentageUsedDisk = (float(usedDisk) / float(totalDisk)) * 100
        logger.info("PERCENTAGE DISK USED: " + str(float(percentageUsedDisk)) + "%")
        print ("For FileSystem: " +str(filesystemItem)+ 
                " the percentage used disk space is: "
                + str(float(percentageUsedDisk)) + "%")
        return percentageUsedBlocks
    except:
        logger.warning("There was an issue gathering disk information, as disk : '"
                        + str(filesystemItem) + "' not in Use")
        return False

def getFilesystems():
    '''
    The getFilesystems def gathers up all the Filesystems in use and calls
    the usedSpace def to return persentage used
    '''
    mountFile = '/etc/mtab'
    filesystems = open(mountFile)
    lines = filesystems.readlines()
    filesystems.close()
    list = []
    for line in lines:
        list.append(line.split()[1])
    UsageDict = {}
    for item in list:
        percentageUsed = usedSpace(item)
        if percentageUsed == False:
            logger.warning("File System : '" +str(item)+ "' Not In Use\n\n")
        else:
            UsageDict[item] = percentageUsed
            logger.info("For FileSystem: '" +str(item)+ 
                        "' Disk Percentage Used info: " +str(percentageUsed)+ "%\n\n")
    return UsageDict

def monitorDiskUsage(filesystem,alerts,threshold,email,hostname):
    '''
    '''
    try:
        sender = config.get('CIFWK', 'cifwkDistributionList')
        if filesystem == "all":
            usageDict = getFilesystems()
            for filesystem,percentageUsed in usageDict.items():
                if alerts == "yes" and percentageUsed >= float(threshold):
                    logger.info("Alerts on and Threshold reached therefore sending alert")
                    subject = ("Disk Usage Alert on host: " +str(hostname))
                    message = ("Disk Usage Alert on host: " +str(hostname)+ ".\n\nThe Current Disk Usage on File System: '" +str(filesystem)+ "' is: " +str(percentageUsed)+ "%.\n\nThe Monitored File System: '" +str(filesystem)+ "' is either equal to or greater than the entered Threshold Value.\n\nThe entered Threashold Value is set at: '" +str(threshold)+ "%'.\n\nPlease investigate.\n\nRegards 'The CIFWK Team'"),
                    try:
                        email = email.split(",")
                        send_mail(subject,message,sender,email, fail_silently=False)
                        logger.info("Alert to email: " +str(email)+ " Sent with success")
                    except Exception as e:
                        logger.error("Alter Email to: " +str(email)+ " Failed to send, Error: " +str(e)) 
        else:
            filesystem = filesystem.split(",")
            for fs in filesystem:
                diskUsage = usedSpace(str(fs))
                logger.info("Returned Percentage Disk Usage: " +str(diskUsage)+ "\n")
                if alerts == "yes" and diskUsage >= float(threshold):
                    logger.info("Alerts on and Threshold reached therefore sending alert")
                    subject = ("Disk Usage Alert on host: " +str(hostname))
                    message = ("Disk Usage Alert on host: " +str(hostname)+ ".\n\nThe Current Disk Usage on File System: '" +str(fs)+ "' is: " +str(diskUsage)+ "%.\n\nThe Monitored File System: '"+str(fs)+ "' is either equal to or greater than the entered Threshold Value.\n\nThe entered Threashold Value is set at: '" +str(threshold)+ "%'.\n\nPlease investigate.\n\nRegards 'The CIFWK Team'")
                    try:
                        email = email.split(",")
                        send_mail(subject,message,sender,email,fail_silently=False)
                        logger.info("Alert to email: " +str(email)+ " Sent with success")
                    except Exception as e:
                        logger.error("Alter Email to: " +str(email)+ " Failed to send, Error: " +str(e))
    except Exception as e:
        return logger.error("Issue with getting Disk Usage Details, Error: " +str(e))

def monitorFileOrDirectorySize(fileSystem,sizeInBytes):
    '''
    The monitorFileOrDirectorySize def is used to monitor the amount of space
    occupied by files on a given filesystem, warning can be sent if
    needed when a large file or directory exists or large amounts of job
    history are stored, this warning is not yet implemented
    '''
    start_path = fileSystem
    for dirpath, dirnames, filenames in os.walk(start_path):
        try:
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.getsize(fp) >= sizeInBytes:
                    logger.info("Consumed Disk Space: " +str(os.path.getsize(fp)) + " Bytes, By File: " +str(fp))
        except Exception as e:
            logger.error("Issue getting all consumed disk space for files in fileSystem: " +str(fileSystem)+
                             ". Error: " +str(e))

def monitorFilesytemRootDirSize(fileSystem):
    '''
    The monitorFilesytemRootDirSize def will return the size of each root directory on a given FileSystem
    Returns a python dict of Key (Directory in File System) and Value (Used Disk Space)
    '''
    try:
        command = "du -sh " + str(fileSystem) + "/* | sort -hr"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd="/tmp")
        output = process.communicate()[0].split()
        #Every second value is Directory and Used Space so converting the list for logger
        outputUpdate = zip(output[0::2], output[1::2])
        for out in outputUpdate:
            logger.info("For Directory: " +str(out[1])+ ", Used Space: " +str(out[0]))
            #The Print is for Jenkins to parse results into csv file
            print ("For Directory: " +str(out[1])+ ", Used Space: " +str(out[0]))
    except Exception as e:
        logger.error("Issue Return the directory sizes, error thrown: " +str(e))

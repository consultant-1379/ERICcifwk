import sys
sys.path.append('/proj/lciadm100/cifwk/latest/')
sys.path.append('/proj/lciadm100/cifwk/latest/django_proj/')
import os
import subprocess
import commands
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_proj.settings'
#from django.core.management import execute_manager
import settings
from django.core.mail import send_mail
from optparse import make_option
import fem.utils
from ciconfig import CIConfig
config = CIConfig()
import logging
logger = logging.getLogger(__name__)
import time
import pika
from datetime import datetime
from daemon import runner
from subprocess import *
logDir = config.get('MESSAGE_BUS', 'logDir')

class App():

    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty' 
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  '/tmp/checkmbdaemon.pid'
        self.pidfile_timeout = 5

    def run(self):
        #start message bus consumer
        time.sleep(10)
        initialMBCheck=call("ps -ef | grep eiffel_monitor_daemon | grep -v grep || exit 1", shell=True)
        if initialMBCheck !=0:
            os.system("/proj/lciadm100/cifwk/latest/etc/init.d/message_bus_daemon start")
        emailCount = 120 
        countDown = False
        checkResult = ""
        while True:
            #30 seconds sleep before checking
            time.sleep(30)
            try:
                checkResult = self.checkProcess()
            except Exception as e:
                logger.error("Issue with checking rabbitmq and message bus daemon, Error: " + str(e))
                checkResult = ["Not Running","Not Running"]
            if "Not Running" in checkResult[0] or "Not Running" in checkResult[1]:
                #Finding process not running.
                retry = 5 
                while (retry !=0):
                    if "Not Running" in checkResult[0] or "Not Running" in checkResult[1]:
                        self.restartDaemons(checkResult)
                        retry = retry-1
                    else:
                        #when processes are restarted
                        logger.info("Successful Recovered")
                        self.recoveredEmail()
                        emailCount = 120
                        countDown = False
                        break
                    try:
                        checkResult = self.checkProcess()
                    except Exception as e:
                        logger.error("Issue with checking rabbitmq and message bus daemon, Error: " + str(e))
                        checkResult = ["Not Running","Not Running"]

                #when after 6 retries failure email is sent
                if (retry == 0 and countDown == False):
                    logger.error("Failure in restarting RabbitMQ and Message Bus Daemon")
                    self.failureEmail()
                    countDown = True
                    emailCount = emailCount -1
                elif (retry == 0 and emailCount == 0):
                    self.failureEmail()
                    emailCount = 120
                elif countDown == True:
                    emailCount = emailCount -1
                        
    def checkProcess(self):
        result = []
        #RabbitMQ Check
        rmq  = commands.getoutput('ps aux')
        if "rabbit" in rmq:
            rabbit = self.rabbitMQcheck()
            if rabbit == "Working":
                result.append("Message Bus Running") 
            else:
                result.append("Message Bus Not Running")
                logger.error("Message Bus Daemon not receiving  messages")
        else:
            result.append("RabbitMQ Not Running")
            logger.error("RabbitMQ Not Running: Process not in ps aux list")

        #Message Bus Daemon Check
        processIdfile = "/tmp/testdaemon.pid"
        tmp = os.path.exists(processIdfile)
        pipe = Popen("ps -ef | grep eiffel_monitor_daemon | grep -v grep | awk '{print $2}'", shell=True, stdout=PIPE).stdout
        output = pipe.read()
        outputs = output.split()
        pids = []
        for o in  outputs:
            pids.append(o)
        if tmp:
            ins = open( processIdfile, "r" )
            list  = []
            for line in ins:
                list.append( line )
            ins.close()
            pid = int(list[0])
            if len(pids) > 1:
                for p in pids:
                    os.system("kill -9 " + str(p))
                result.append("Message Bus Not Running")
                logger.error("Message Bus Daemon Not Running: After Finding More Than One Message Bus Daemon Process ID")
            else:
                try:
                    os.kill(pid, 0)
                    result.append("Message Bus Running")
                except OSError:
                    result.append("Message Bus Not Running")
                    logger.error("Message Bus Daemon Not Running: PID not responsive")
        else:
            if len(pids) > 1:
                for p in pids:
                    os.system("kill -9 " + str(p))
                result.append("Message Bus Not Running")
                logger.error("Message Bus Daemon Not Running: After Finding More Than One Message Bus Daemon Process ID")
            elif len(pids) == 1:
                 result.append("Message Bus Running")
            else:
                 result.append("Message Bus Not Running")
                 logger.error("Message Bus Daemon Not Running: No PID found")
        
        return result

    def messageSender(self):
        # Sending message to the Message Bus Receiver (eiffel_monitor_daemon)
        broker_host = config.get('MESSAGE_BUS', 'hostname')
        exchange_to_monitor =  config.get('MESSAGE_BUS', 'exchangeName')
        binding_keys = config.get('MESSAGE_BUS', 'bindingKeys')
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange_to_monitor, type='topic', durable=False)
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.CRITICAL)
        message = "CIFWKMBCHECK : "+ str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        channel.basic_publish(exchange=exchange_to_monitor,
                routing_key='#',
                body=str(message))
        connection.close()

    
    def rabbitMQcheck(self):
        #Check if Message was Received
        result = ""
        os.system('touch /tmp/checkrmq.log')
        try:
            self.messageSender()
        except:
            result = "Not Working"
            return result
        #60 seconds sleep before checking
        time.sleep(60)
        ins = open( "/tmp/checkrmq.log", "r" )
        lines = []
        for line in ins:
            lines.append( line )
        if lines:
            if "CIFWKMBCHECK" in lines[0]:
                result = "Working"
            else:
                result = "Not Working"
        else:
            result = "Not Working"
        os.system('rm /tmp/checkrmq.log')
        return result
    
    def restartDaemons(self, checkResult):
        try:
            if "RabbitMQ Not Running" not in checkResult[0] and "RabbitMQ Not Running" not in checkResult[1]:
                logger.info("Attempting Message Bus Daemon restart")
                os.system("/proj/lciadm100/cifwk/latest/etc/init.d/message_bus_daemon stop")
                time.sleep(10)
                os.system("/proj/lciadm100/cifwk/latest/etc/init.d/message_bus_daemon start")
                time.sleep(20)
                try:
                    checkResult = self.checkProcess()
                except Exception as e:
                    logger.error("Issue with checking rabbitmq and message bus daemon, Error: " + str(e))
                    checkResult = ["Not Running","Not Running"]
            if "Not Running" in checkResult[0] or "Not Running" in checkResult[1]:
                logger.info("Message Bus Daemon restart failed, Attempting rabbit MQ and Message Bus Daemon restart")
                # Start/restart RabbitMQ &  Message Bus Daemon listener
                os.system("/proj/lciadm100/cifwk/latest/etc/init.d/message_bus_daemon stop")
                time.sleep(10)
                os.system("/proj/lciadm100/cifwk/latest/etc/init.d/cifwk-rabbittmq stop")
                time.sleep(20)
                os.system("/proj/lciadm100/cifwk/latest/etc/init.d/cifwk-rabbittmq start")
                time.sleep(20)
                os.system("/proj/lciadm100/cifwk/latest/etc/init.d/message_bus_daemon start")
                time.sleep(20)
        except Exception as e:
            logger.error("Issue with restarting rabbitmq and message bus daemon, Error:" + str(e))



    def failureEmail(self):
        #Restart Fails Send Email
        to = []
        dm = 'CI-Framework@ericsson.com'
        email = config.get("CIFWK", "cifwkDistributionList")
        to.append(email)
        header = "Error: Message Bus Failed to Restart"
        content = "Please check Message Bus Daemon and RabbitMQ\n. Message_bus_daemon_monitor was unable to restart the procsses, RabbitMQ and Message Bus Daemon listener are currently not running.\n"
        send_mail(header, content, dm, to, fail_silently=False)

    def recoveredEmail(self):
        #Recovered Send Email
        to = []
        dm = 'CI-Framework@ericsson.com'
        email = config.get("CIFWK", "cifwkDistributionList")
        to.append(email)
        header = "Recovered: Message Bus has been Restarted"
        content = "Message_bus_daemon_monitor was able to restart the procsses, RabbitMQ and Message Bus Daemon listener are currently running.\n"
        send_mail(header, content, dm, to, fail_silently=False)


                
app = App()
logger = logging.getLogger("DaemonLog")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.FileHandler(logDir+"messagebuscheck.log")
handler.setFormatter(formatter)
logger.addHandler(handler)
daemon_runner = runner.DaemonRunner(app)
#This ensures that the logger file handle does not get closed during daemonization
daemon_runner.daemon_context.files_preserve=[handler.stream]
daemon_runner.do_action()


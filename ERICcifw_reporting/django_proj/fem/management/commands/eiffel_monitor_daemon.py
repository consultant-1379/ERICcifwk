import sys
sys.path.append('/proj/lciadm100/cifwk/latest/')
sys.path.append('/proj/lciadm100/cifwk/latest/django_proj/')
sys.path.append('/proj/lciadm100/cifwk/latest/lib/python/')
sys.path.append('/proj/lciadm100/cifwk/latest/lib/python/site-packages/')
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_proj.settings'
#from django.core.management import execute_manager
import settings
import pika
from optparse import make_option
import fem.utils
from ciconfig import CIConfig
config = CIConfig()
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
from daemon import runner
import shutil
import ast
logDir = config.get('MESSAGE_BUS', 'logDir')



class App():

    def __init__(self):
        if os.path.isfile(logDir+"messagebus.log"):
            try:
                shutil.copyfile(logDir+"messagebus.log",logDir+"messagebus."+ str(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))+".log")
            except:
                logger.error("Unable to copy log file")
        self.stdin_path = '/dev/null'
        self.stdout_path = logDir+"messagebus.log"
        self.stderr_path = logDir+"messagebus.log"
        self.pidfile_path =  '/tmp/testdaemon.pid'
        self.pidfile_timeout = 5

    def run(self):
        queue_name = config.get('MESSAGE_BUS', 'queueName')
        broker_host = config.get('MESSAGE_BUS', 'hostname')
        exchange_to_monitor =  config.get('MESSAGE_BUS', 'exchangeName')
        binding_keys = ast.literal_eval(config.get('MESSAGE_BUS', 'bindingKeys'))
        debugFlag = config.get('MESSAGE_BUS', 'debugFlag')
        debugFlag = int(debugFlag)
        latestVersion = config.get('MESSAGE_BUS', 'latestVersion')
        mbUser = config.get('MESSAGE_BUS', 'mbFunctionalUser')
        mbPwd = config.get('MESSAGE_BUS', 'mbFunctionalUserPassword')
        mbURL = 'amqps://' + mbUser + ':' + mbPwd + '@'+ broker_host + '/%2F'
        connectionMB = pika.BlockingConnection(pika.URLParameters(mbURL))
        channelMB = connectionMB.channel()
        channelMB.exchange_declare(exchange=exchange_to_monitor, type='topic', durable=True, passive=True)
        result = channelMB.queue_declare(queue=queue_name, durable=True, passive=True)

        for binding_key in binding_keys:
            channelMB.queue_bind(exchange=exchange_to_monitor,
                       queue=queue_name,
                       routing_key=binding_key)

        def callback(ch, method, properties, body):
            if "artifact.modified" in method.routing_key:
                try:
                    logger.info("##### Eiffel message pre check ######")
                    logger.info(body)
                    fem.utils.consumeEiffelArtifactModifiedMessage(body,debugFlag,latestVersion)
                except Exception as e:
                    logger.error("Issue with message: "+str(e))

        channelMB.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True,
                      exclusive=True)
        try:
            channelMB.start_consuming()
        except Exception as e:
            logger.error("Issue with message bus consumer: " + str(e))

app = App()
logger = logging.getLogger("DaemonLog")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.FileHandler(logDir+"messagebus.log")
handler.setFormatter(formatter)
logger.addHandler(handler)

daemon_runner = runner.DaemonRunner(app)
#This ensures that the logger file handle does not get closed during daemonization
daemon_runner.daemon_context.files_preserve=[handler.stream]
daemon_runner.do_action()



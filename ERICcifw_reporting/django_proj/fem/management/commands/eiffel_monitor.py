import pika
import json

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from fem.models import *
import fem.utils


import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run Message Bus eiffel monitor"
    option_list = BaseCommand.option_list  + (
            make_option('--hostname',
                dest='hostname',
                help='Message Bus hostname'),
            make_option('--exchangeName',
                dest='exchangeName',
                help='Message Bus exchange name'),
            make_option('--bindingKeys',
                dest='bindingKeys',
                help='binding keys or by default DomainId.#'),
            make_option('--store-job-data',
                dest='storeJobData',
                help='set to true to store the job data in the CI DB'),
            )


    def handle(self, *args, **options):
        broker_host = None
        if options['hostname'] is None:
            raise CommandError("You need to provide a Message Bus hostname")
        else:
            print str(options['hostname'])
            broker_host = options['hostname']
        exchange_to_monitor = None
        if options['exchangeName'] is None:
            raise CommandError("You need to provide a Message Bus Exchange Name")
        else:
            exchange_to_monitor = options['exchangeName']
        binding_keys = None
        if options['bindingKeys'] != None:
            binding_keys = options['bindingKeys']
        else:
            binding_keys = ['#']

        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
        channel = connection.channel()
        # TODO should use a durable exchange (modified for the sprint 4 demo)!
        channel.exchange_declare(exchange=exchange_to_monitor, type='topic', durable=False)
        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        for binding_key in binding_keys:
            channel.queue_bind(exchange=exchange_to_monitor,
                       queue=queue_name,
                       routing_key=binding_key)

        print ' [*] Waiting for messages. To exit press CTRL+C'
        print "     broker = %r, exchange = %r, routing keys = %r" % (broker_host, exchange_to_monitor, binding_keys)

        def callback(ch, method, properties, body):
            prettyPrintedMessage = fem.utils.prettyPrintJsonString(body)
            if "artifact.modified" in method.routing_key:
                fem.utils.consumeEiffelArtifactModifiedMessage(body)
            print " [x] %s :\n %s" % (method.routing_key, prettyPrintedMessage)
            if ( options['storeJobData'] is not None ): 
                if "job.finished" in method.routing_key:
                    job = json.loads(body)
                    fem.utils.collectJobStatusInfoMessageBus(job)
                   

        channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

        channel.start_consuming()


    
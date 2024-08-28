from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create label and Components"
    option_list = BaseCommand.option_list  + (
            make_option('--label',
                dest='label',
                help='name of the label'),
            make_option('--parent',
                dest='parent',
                help='name of the parent'),
            make_option('--child',
                dest='child',
                help='name of the child'),
            make_option('--product',
                dest='product',
                help='name of the product'),
            )

    def handle(self, *args, **options):

        if options['label'] is None:
            raise CommandError("You need to provide a name for the label")
        if options['parent'] is None:
            raise CommandError("You need to provide a name for the parent")
        if options['child'] is None:
            raise CommandError("You need to provide a name for the child")
        if options['product'] is None:
            raise CommandError("You need to provide a name for the product")

        parent = str(options['parent'])
        child = str(options['child'])
        labelName = str(options['label'])
        product = str(options['product'])

        try:
            product = Product.objects.get(name=product)
            label = Label.objects.create(name=labelName)
            dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error("Issue "+str(e))
            return "Error"
        try:
            label = Label.objects.get(name=labelName)
            parent = Component.objects.create(product=product, label=label, element=parent, dateCreated=dateCreated)
            child = Component.objects.create(product=product, label=label, parent=parent, element=child, dateCreated=dateCreated)
            return "OK"
        except Exception as e:
            logger.error("Issue "+str(e))
            return "Error"

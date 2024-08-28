from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from dmt.models import *
import logging


class Command(BaseCommand):
    help = "Create Ip Range item and IP Range start,end,subnet and gateway items for the IP Range Item, for all KVM deployment types."
    option_list = BaseCommand.option_list

    def handle(self, *args, **options):
        ipRangeItem = ""
        kvm_clusters = Cluster.objects.filter(layout__name="KVM")
        for kvm_cluster in kvm_clusters:
            ipIdNum = str(kvm_cluster.id)
            if len(str(kvm_cluster.id)) == 3:
                ipIdNum = "5" + str(kvm_cluster.id)

            start_ip = "fd5b:1fd5:8295:" + str(ipIdNum) + "::2"
            end_ip = "fd5b:1fd5:8295:" + str(ipIdNum) + "::c900"
            bitmask = "64"
            gateway = "fd5b:1fd5:8295:" + str(ipIdNum) + "::"
            try:
                if not IpRangeItem.objects.filter(ip_range_item="ClusterId_"+str(kvm_cluster.id)).exists():
                    ipRangeItem = IpRangeItem.objects.create(ip_range_item="ClusterId_"+str(kvm_cluster.id))
                    logger.info("IP Range Item Created: " + str(ipRangeItem))
                    ipRange = IpRange.objects.create(ip_range_item=ipRangeItem,start_ip=start_ip,end_ip=end_ip,bitmask=bitmask,gateway=gateway)
                    logger.info("IP Range Created: " + str(ipRange))
            except Exception as error:
                logger.error("There was an issue creating IP Ranges for Cluster: " + str(kvm_cluster.name) + ", Error: " + str(error))

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils

import random

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Don't run this on a live system, you muppet!"
    type = "rpm"

    def handle(self, *args, **options):
        solsets = {
                "common": "CXP1000001",
                "cpp_pm_mediation": "CXP1000002",
                "com_ecim_pm_mediation": "CXP1000003",
                "mediation": "CXP1000004",
                "pm_mediation": "CXP1000005",
                "topology": "CXP1000006",
        }
        packages = [["ERICpmmedcore_CXP9030102","CXP9030102", "PM Mediation Core", "pm_mediation"],
                    ["ERICpmmedcom_CXP9030103","CXP9030103", "PM Mediation Common", "pm_mediation"],
                    ["ERICpmservice_CXP9030101","CXP9030101", "PM Service", "pm_mediation"],
                    ["ERICcpppmmed_CXP9030107","CXP9030107", "CPP PM Mediation", "cpp_pm_mediation"],
                    ["ERICcomecimpmmed_CXP9030108","CXP9030108", "COM/ECIM PM Mediation", "com_ecim_pm_mediation"],
                    ["ERICtopserv_CXP9030160","CXP9030160", "Topology Service", "topology"],
                    ["ERICdatapers_CXP9030106", "CXP9030106", "Data Persistence Service", "common"],
                    ["ERICeventserv_CXP9030157", "CXP9030157", "Event Service", "common"],
                    ["ERICservfwk_CXP9030097", "CXP9030097", "Service Framework", "common"],
                   ]

        for solset in solsets.keys():
            print "Solset: " + solset + " ; pnum: " + solsets[solset]
            cireports.utils.createSolutionSet(solset, solsets[solset])
            # Create one version of the solution set
            SolutionSetRevision.objects.create(solution_set=SolutionSet.objects.get(name=solset), version="1.0.1")

        # Create some TOR releases and drops
        releases = {
                "1.0": [[1,2,3,4,5,6,7,8,9,10,11,12,13,14], None],
                "1.1": [[1,2,3,4,5,6], "1.0.11"],
                "2.0": [[1,2,3,4,5,6,7,8,9], "1.1.4"],
                "3.0": [[1,2,3,4,5,6,7,8,9,10,11], "2.0.7"]
        }
        base = None
        for rel in sorted(releases.keys()):
            try:
                cireports.utils.createRelease("TOR " + rel)
                base = releases[rel][1]
                logger.info("Release Created: " +str(rel))
            except Exception as e:
                logger.error("Unable to create Relaese: " +str(rel)+
                        " Error Thrown " +str(e))
            for num in releases[rel][0]:
                if (base != None):
                    logger.info("Creating drop " + rel + "." + str(num) + " with base " + base)
                else:
                    logger.info("Creating drop " + rel + "." + str(num))
                try:
                    cireports.utils.createDrop(rel + "." + str(num), "TOR " + rel, base)
                    logger.info("Drop Created with Success" +rel + "."
                        + str(num), "TOR " + rel, base)
                except Exception as e:
                    logger.error("Unable to create Drop" +rel + "."
                        + str(num), "TOR " + rel, base + " Error Thrown: "
                        +str(e))

                base = rel + "." + str(num)

        for p in packages:
            #print "Creating package " + p[0] + " - " + p[1]
            try:
                cireports.utils.createPackage(p[0], p[1], "eeicjon", p[2])
                logger.info("Creating package " + p[0] + " - " + p[1])
            except Exception as e:
                logger.error("Unable to create package " + p[0] + " - " + p[1])
                return False
            # add to a solution set
            '''
            TO DO: Investigate Solution set handling when implemented therefore below commented out
            until this investigation is carried out
            '''
            #print " -- adding to sol set: " + p[3]
            #try:
                #SolutionSetContents.objects.create(solution_set_rev=SolutionSetRevision.objects.get(solution_set__name=p[3]), package=Package.objects.get(name=p[0]))
                #SolutionSetContents.objects.create(solution_set_rev=SolutionSetRevision.objects.get(SolutionSet.objects.get(name=test1), package=Package.objects.get(name=test2)))
            #    logger.error("Adding to sol set: " + p[3])
            #except Exception as e:
            #    logger.error("Unable to add to sol set: " + p[3])
            #    return False
            # Create a few revisions of the package
            maj = 1
            min = 0
            patch = 1
            for rel in sorted(releases.keys()):
                # deliver randomly, 50% chance of delivering in a particular drop,
                if (random.randint(0,1) == 1):
                    maj += 1
                else:
                    min += 1
                for num in releases[rel][0]:
                    if (random.randint(0,1) == 1):
                        ver = str(maj) + "." + str(min) + "." + str(patch)
                        try:
                            package_rev = cireports.utils.createPackageRevision(p[0], ver, type,
                                                str(random.randint(0,1000)), str(random.randint(0,1000)))
                            logger.info("Creted Package Rev with Success")
                        except Exception as e:
                            logger.error("Unable to create Package Revision, Error Thrown "
                                    +str(e))
                            return False
                        try:
                            dpm = DropPackageMapping.objects.create(package_revision=package_rev, released=1, drop=Drop.objects.get(name=rel + "." + str(num)))
                            logger.info("Created Package Mapping with Success")
                        except Exception as e:
                            logger.error("Unable to create Package Mapping, Error Thrown: "
                                    +str(e))
                            return False
                        patch += 1
                        

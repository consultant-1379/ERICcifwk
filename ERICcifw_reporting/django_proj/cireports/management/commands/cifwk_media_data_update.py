from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            releases = Release.objects.all()
            for rel in releases:
                release = Release.objects.get(id=rel.id)
                logger.info("Release: " + str(release.name))
                if (release.iso_artifact):
                    isoArtifact = release.iso_artifact
                    description = "Media Artifact For Release " + str(release.name)
                    if MediaArtifact.objects.filter(name=isoArtifact).exists():
                        mediaArtifact  = MediaArtifact.objects.get(name=isoArtifact)
                        logger.info("Media Artifact: " + str(mediaArtifact))
                        release.masterArtifact = mediaArtifact
                        release.save()
                    else: 
                        if "OSS-RC" in str(release.product.name) and "OSSISO" in str(isoArtifact):
                            [iso, number] = str(isoArtifact).split("-")
                            if "OSSISO_1" in isoArtifact:
                                number = '1'.join(str(number).rsplit('X', 1))
                            elif "OSSISO_2" in isoArtifact:
                                number = '2'.join(str(number).rsplit('X', 1))
                            else:
                                number = '3'.join(str(number).rsplit('X', 1))
                        else:
                            [iso, number] = str(isoArtifact).split("_")
                        mediaArtifact = MediaArtifact.objects.create(name=isoArtifact, number=number, description=description)
                        logger.info("Media Artifact New: " + str(mediaArtifact))
                        release.masterArtifact = mediaArtifact
                        release.save()
                    drops = Drop.objects.filter(release__id=release.id)
                    for drp in drops:
                        logger.info("Drop " + str(drp))
                        if ISObuild.objects.filter(drop__id=drp.id).exists():
                            mediaArtVers = ISObuild.objects.filter(drop__id=drp.id)
                            for ma in mediaArtVers:
                                mav =  ISObuild.objects.get(id=ma.id)
                                logger.info("Media Artifact version " + str(mav))
                                mav.mediaArtifact = mediaArtifact
                                mav.artifactId = isoArtifact
                                mav.groupId = release.iso_groupId
                                mav.arm_repo = release.iso_arm_repo
                                mav.save()
        except Exception as e:
            raise CommandError("Does Not Exist in Database - " + str(e))


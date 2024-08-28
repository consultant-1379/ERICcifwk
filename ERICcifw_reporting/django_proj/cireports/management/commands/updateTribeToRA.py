from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime
from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            teamLabel = Label.objects.get(name="Team")
            parentLabel = Label.objects.get(name="Tribe")
            parentLabel.name = "RA"
            parentLabel.save()
            product = Product.objects.get(name="ENM")
            PlanningAndConfigurationTeams = ['Doozers', 'Fusion', 'TeamAmerica', 'TheAvengers', 'Vedas', 'Totoro', 'Apollo', 'Pepperoni', 'Vindhyas', 'ROPStars', 'BlueSky', 'Atlas', 'Odin', 'ScrumU', 'Dakka', 'Cybermen', 'Shogun', 'Samurai', 'Ninjas', 'Ajeya', 'Thalaiva', 'Titans', 'Trident', 'Zenith']
            AssuranceAndOptimisingTeams = ['Dhruva', 'Jupiter', 'Mars', 'Europa', 'Magrathea', 'Quasar', 'Tatooine', 'Cumulus', 'Heisenberg', 'Mercury', 'Bazinga', 'Volt', 'Buccaneers', 'Dynamo', 'Sunrise', 'Insert_Name_Here', 'Autobots', 'Burgundy', 'XMEN', 'Denali', 'BadIntentions', 'Teapot', 'Emperors', 'Challengers', 'Decepticons', 'Bazinga']
            TransportTeams = ['Endeavour', 'Gladiators', 'CreativeCoders', 'Quarks', 'Hack', 'X-Files', 'LinksAwakening', 'WindWaker', 'SkywardSword', 'TheGoonies', 'Alchemists', 'Guinness']
            SecurityTeams = ['Curiosity', 'ENMeshed', 'Jcoholics', 'Nemesis', 'Painkillers', 'SpiceGirls', 'Critters', 'District11', 'Skyfall', 'The16thFloor', 'Abhedya', 'Ciphers', 'Classic', 'Nirvana']
            NetworkEvolutionAndOSSTeams = ['J-Team', 'Oasis', 'Redemption', 'MediationSDK', 'UISDK', 'Deliverance', 'Trigger', 'TheATeam', 'TheFourth', 'RadioForce', 'Boru', 'Venus', 'Eklavya', 'Fortress', 'TheBruisers', 'Voyager', 'Hooligans', 'Dougal', 'Inappropriates', 'Lumberjacks', 'Vandals', 'Chaos', 'Screwloose', 'LooneyTunes', 'Mjolnir', 'Chanakya', 'Warriors', 'Fenrir', 'Sovereign', 'Fargo', 'D3', 'BigTrick', 'Vulcanians', 'Defiant', 'Sentinels', 'Smart', 'Mavericks', 'SlidingDoors']
            MenInBlackTeams = ['DespicableUs', 'Legolas', 'FlyingGalahad', 'Unacceptables']
            raList = ['PlanningAndConfiguration', 'AssuranceAndOptimising', 'Transport', 'Security', 'NetworkEvolutionAndOSS', 'MenInBlack']
            for raItem in raList:
                dateCreated= datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    parentElementComp = Component.objects.get(element=raItem, product=product)
                except:
                    parentElementComp = Component.objects.create(element=raItem, product=product, label=parentLabel, dateCreated=dateCreated)
                if raItem == 'PlanningAndConfiguration':
                    for teamItem in PlanningAndConfigurationTeams:
                        try:
                            teamComp = Component.objects.get(element=teamItem)
                            teamComp.parent = parentElementComp
                            teamComp.save()
                            logger.info("UPDATED: " + str(teamComp))
                        except:
                            teamComp = Component.objects.create(element=teamItem, product=product, parent=parentElementComp, label=teamLabel, dateCreated=dateCreated)
                            logger.info("CREATED: " + str(teamComp))
                if raItem == 'AssuranceAndOptimising':
                    for teamItem in AssuranceAndOptimisingTeams:
                        try:
                            teamComp = Component.objects.get(element=teamItem)
                            teamComp.parent = parentElementComp
                            teamComp.save()
                            logger.info("UPDATED: " + str(teamComp))
                        except:
                            teamComp = Component.objects.create(element=teamItem, product=product, parent=parentElementComp, label=teamLabel, dateCreated=dateCreated)
                            logger.info("CREATED: " + str(teamComp))
                if raItem == 'Transport':
                    for teamItem in TransportTeams:
                        try:
                            teamComp = Component.objects.get(element=teamItem)
                            teamComp.parent = parentElementComp
                            teamComp.save()
                            logger.info("UPDATED: " + str(teamComp))
                        except:
                            teamComp = Component.objects.create(element=teamItem, product=product, parent=parentElementComp, label=teamLabel, dateCreated=dateCreated)
                            logger.info("CREATED: " + str(teamComp))
                if raItem == 'Security':
                    for teamItem in SecurityTeams:
                        try:
                            teamComp = Component.objects.get(element=teamItem)
                            teamComp.parent = parentElementComp
                            teamComp.save()
                            logger.info("UPDATED: " + str(teamComp))
                        except:
                            teamComp = Component.objects.create(element=teamItem, product=product, parent=parentElementComp, label=teamLabel, dateCreated=dateCreated)
                            logger.info("CREATED: " + str(teamComp))
                if raItem == 'NetworkEvolutionAndOSS':
                    for teamItem in NetworkEvolutionAndOSSTeams:
                        try:
                            teamComp = Component.objects.get(element=teamItem)
                            teamComp.parent = parentElementComp
                            teamComp.save()
                            logger.info("UPDATED: " + str(teamComp))
                        except:
                            teamComp = Component.objects.create(element=teamItem, product=product, parent=parentElementComp, label=teamLabel, dateCreated=dateCreated)
                            logger.info("CREATED: " + str(teamComp))
                if raItem == 'MenInBlack':
                    for teamItem in MenInBlackTeams:
                        try:
                            teamComp = Component.objects.get(element=teamItem)
                            teamComp.parent = parentElementComp
                            teamComp.save()
                            logger.info("UPDATED: " + str(teamComp))
                        except:
                            teamComp = Component.objects.create(element=teamItem, product=product, parent=parentElementComp, label=teamLabel, dateCreated=dateCreated)
                            logger.info("CREATED: " + str(teamComp))
        except Exception as e:
            raise CommandError("Does Not Exist in Database - " + str(e))


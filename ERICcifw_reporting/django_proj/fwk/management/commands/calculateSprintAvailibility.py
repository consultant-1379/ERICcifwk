import logging
logger = logging.getLogger(__name__)
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    '''
    '''
    help = "\n\
            Calculate the Percentage of time to allocate in a Sprint to, Development, Innovation and Other Work(Bugs,Support,Mails,Mettings etc...)\n\
           "
    option_list = BaseCommand.option_list  + (

            make_option('--includeInnovationTime [Manually add Innovation Time]',
                dest='includeInnovationTime',
                help='[Optional] Default Behaviour of script, include innovation time.'),
            make_option('--innovationPrecentageFromTotalDays [Precenatge of Inovation Time from Total Days]',
                dest='innovationPrecentageFromTotalDays',
                help='[Optional] Take a defined percentage off Total Sprint Days for innovation.'),
            make_option('--innovationPrecentageFromDevelopmentPercentage [Precenatge of Inovation Time from Development Percentage]',
                dest='innovationPrecentageFromDevelopmentPercentage',
                help='[Optional] Take a defined percentage off Development Percentage Days for innovation.'),
            make_option('--totalDays [Total Sprint Days]',
                dest='totalDays',
                help='[Required] Please enter the total amount of days in the sprint per team memmber excluding weekends, annaul leave, training, innovation etc ...'),
            make_option('--teamSize [Total Team Size]',
                dest='teamSize',
                help='[Optional] Please enter the total of people available for Sprint.'),
            make_option('--absenceDays [Days Missing for AL / Training ]',
                dest='absenceDays',
                help='[Optional] Please enter the total number of days for Annual Leave, Training etc... in Sprint'),
            make_option('--innovationDays [Total Number if Innovation Days in Sprint]',
                dest='innovationDays',
                help='[Opional] Please enter the total amount of days in the sprint allocated to innovation.'),
            make_option('--developmentPercentage [Development Sprint Percentage]',
                dest='developmentPercentage',
                help='[Required] Please enter the percentage allocated for developement time for the sprint.'),
            make_option('--otherWorkPercentage [Work Sprint Percentagc]',
                dest='otherWorkPercentage',
                help='[Optional] Please enter the percentage allocated for other work time for the sprint.'),
            )

    def handle(self, *args, **options):

        logger.info('############################################################')
        logger.info('############################################################')
        logger.info('############################################################')
        oneHundredPresent = float(100)
        if options['totalDays'] == None:
            raise CommandError("Please enter the total amount of days in a sprint before continuing.")
        else:
            totalDays = float(options['totalDays'])
            logger.info('Total Days: ' + str(int(round(totalDays))) + " Days.")

        teamSize = 1.0
        if options['teamSize'] != None:
            teamSize = float(options['teamSize'])
        logger.info('Team Size: ' + str(int(round(teamSize))) + " People.")
        totalDays = totalDays * teamSize

        absenceDays = 0.0
        if options['absenceDays'] != None:
            absenceDays = float(options['absenceDays'])
        logger.info('Absence Days: ' + str(int(round(absenceDays))) + " Days.")
        totalDays = totalDays - absenceDays

        innovationDays = 0.0
        if options['innovationPrecentageFromDevelopmentPercentage'] != None or options['innovationPrecentageFromTotalDays'] != None:
            if options['innovationPrecentageFromTotalDays'] != None:
                innovationDaysPercentage = float(options['innovationPrecentageFromTotalDays'])
                innovationDays = innovationDaysPercentage*(totalDays/oneHundredPresent)
            elif options['innovationPrecentageFromDevelopmentPercentage'] != None:
                innovationDays = 0.0
        else:
            if options['innovationDays'] != None:
                innovationDays = float(options['innovationDays']) * teamSize
        print availableDays
        developmentDays = 0.0
        if options['developmentPercentage'] == None:
            raise CommandError("Please enter the percentage allocated for developement time for the sprint before continuing.")
        else:
            developmentPercentage = float(options['developmentPercentage'])
            if options['innovationPrecentageFromDevelopmentPercentage']:
                innovationPrecentageFromDevelopmentPercentage = float(options['innovationPrecentageFromDevelopmentPercentage'])
                innovationPercentage = developmentPercentage*(innovationPrecentageFromDevelopmentPercentage/oneHundredPresent)
                developmentPercentageIncInnovation = developmentPercentage*(developmentPercentage/oneHundredPresent)
                innovationDays = innovationPercentage*(totalDays/oneHundredPresent)
                developmentDays = developmentPercentageIncInnovation*(totalDays/oneHundredPresent)

        logger.info('Innovation Days: ' + str(int(round(innovationDays))) + " Days.")

        if options['otherWorkPercentage'] == None:
            otherWorkPercentage = 0.0
            developmentPercentage = oneHundredPresent
        else:
            otherWorkPercentage = float(options['otherWorkPercentage'])
        logger.info('Development Precentage: ' + str(int(round(developmentPercentage))) + "%.")
        logger.info('Other Work Precentage: ' + str(int(round(otherWorkPercentage))) + "%.")

        if (developmentPercentage + otherWorkPercentage) != 100:
            raise CommandError("Develeopment Percentage and Other Work Percentage must equal 100, Please try again.")

        logger.info('############################################################')
        logger.info('############################################################')
        logger.info('############################################################')

        logger.info("Total Available Days in Sprint: " + str(availableDays) + " Days ~= " + str(int(round(availableDays))) + " Days.")

        if developmentDays == 0:
            developmentDays = (developmentPercentage)*(availableDays/oneHundredPresent)
        logger.info("Total Development Available in Sprint: " + str(developmentDays) + " Days ~= " + str(int(round(developmentDays))) + " Days.")
        otherWorkDays = otherWorkPercentage*(availableDays/oneHundredPresent)
        logger.info("Total Other Work Availbale in Sprint: " + str(otherWorkDays) + " Days ~= " + str(int(round(otherWorkDays))) + " Days.")
        sprintDevelopmentPercentage = developmentDays*(oneHundredPresent/totalDays)
        logger.info("Total Sprint Development Percentage: " + str(sprintDevelopmentPercentage) + "% ~= " + str(int(round(sprintDevelopmentPercentage))) + "%." )

        sprintOtherWorkPercenatge = otherWorkDays*(oneHundredPresent/totalDays)
        logger.info("Total Sprint Other Work Percentage: " + str(sprintOtherWorkPercenatge) + "% ~= " + str(int(round(sprintOtherWorkPercenatge))) + "%.")
        sprintInnovationPercentage = innovationDays*(oneHundredPresent/totalDays)
        logger.info("Total Sprint Innovation Percentage: " + str(sprintInnovationPercentage) + "% ~= " + str(int(round(sprintInnovationPercentage))) + "%.")

        sprintPointsExpected = availableDays*(sprintDevelopmentPercentage/oneHundredPresent)
        logger.info("Total Points expected to be delived in Sprint: " + str(sprintPointsExpected) + " points ~= " + str(int(round(sprintPointsExpected))) + " points.")
        totalSprintPercentage = sprintDevelopmentPercentage + sprintOtherWorkPercenatge + sprintInnovationPercentage
        logger.info("Total Sprint Percentage: " + str(int(round(totalSprintPercentage))) + "%.")

        logger.info('############################################################')
        logger.info('############################################################')
        logger.info('############################################################')

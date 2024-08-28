from excellence.models import *
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render
from django.core.context_processors import csrf
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
from django.core.mail import send_mail
from django.core.validators import validate_email

import logging
logger = logging.getLogger(__name__)
config = CIConfig()

from datetime import datetime, timedelta
from excellence.forms import *
import excellence.utils
from django.contrib.auth.models import User, Group
from guardian.decorators import permission_required, permission_required_or_403
from guardian.conf import settings as guardian_settings
from guardian.exceptions import GuardianError
from guardian.shortcuts import assign
from guardian.shortcuts import get_perms
from guardian.core import ObjectPermissionChecker
from distutils.version import LooseVersion
from django.db import transaction
from fwk.utils import pageHitCounter

def showQuestions(request):
    '''
    The showQuestions function renders the showQuestions html page with all questions in database
    '''
    pageHitCounter("ExcellenceQuestions", None, str(request.user))
    questions = Question.objects.all()
    return render(request, "excellence/showQuestions.html" , {'questions': questions},)

def showCategory(request):
    '''
    '''
    categories = Category.objects.all()
    return render(request, "excellence/showCategories.html" , {'categories': categories},)

def showOrganistaion(request):
    '''
    '''
    pageHitCounter("ExcellenceOrganisation", None, str(request.user))
    organistions = Organisation.objects.all()
    return render(request, "excellence/showOrganisations.html" , {'organistions': organistions},)

@login_required
def addQuestion(request):
    '''
    The addQuestion function allows the user to register a question
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Finish..."
    fh.title = "Add Question"
    fh.redirectTarget = "/excellence/showQuestions"
    fh.form = QuestionForm()
    if request.method == 'POST':
        lowLevel = str(request.POST.get('low_level'))
        if ( LooseVersion(lowLevel) > "5.0" ):
            fh.message = "Oops Low Level must must Less than or equal to 5"
            return fh.display()
        fh.form = QuestionForm(request.POST)
        if fh.form.is_valid():
            try:
                question = fh.form.save(commit=False)
                question.save()
                return fh.success()
            except Exception as e:
                logger.error("Unable to save " +str(question)+ " to database: " +str(e))
                return fh.failure()
        else:
            logger.error("Form was not Valid: " +str(fh.form.errors))
            return fh.failure()
    else:
        return fh.display()


@login_required
def addCategory(request):
    '''
    The addCategory function allows the user to register a category
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Finish..."
    fh.title = "Add Category"
    fh.redirectTarget = "/excellence/showCategories"
    if request.method == 'POST':
        fh.form = CategoryForm(request.POST)
        version = request.POST.get('version')
        name = request.POST.get('name')
        try:
            categoryObj = Category.objects.get(name=name,version=version)
            fh.message = "Oops Version: " +str(version)+ " Already Exists for: " +str(name)+ " please try Again"
            return fh.display()
        except:
            logger.info("Version Selected OK continue")
        if fh.form.is_valid():
            try:
                category = fh.form.save(commit=False)
                category.save()
                return fh.success()
            except Exception as e:
                logger.error("Unable to save " +str(category)+ " to database: " +str(e))
                return fh.failure()
        else:
            logger.error("Form was not Valid: " +str(fh.form.errors))
            return fh.failure()
    else:
        fh.form = CategoryForm()
        return fh.display()

@login_required
def addOrganistaion(request):
    '''
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Finish..."
    fh.title = "Add Organisation"
    fh.redirectTarget = "/excellence/showOrganisations/"
    fh.form = OrganisationForm(initial={'type': "Team",})
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        parent = request.POST.get('parent_Area')
        type = request.POST.get('type')
        if parent == "None":
            orgObj = None 
        else:
            orgObj = Organisation.objects.get(name=str(parent))
        try:
            organisation, created = Organisation.objects.get_or_create(
                                            name=name,
                                            description=description,
                                            owner=request.user,
                                            parent=orgObj,
                                            type=type)
            logger.info("Organistaion: " +str(organisation)+ " added with success")
        except Exception as e:
            logger.error("Unable to add Organistaion Error: " +str(e))
            return fh.failure()
        if type != "Team":
            fh.message = ("Please continue to add  a Full Organisational Tree until Team Level is reached")
            return fh.display()
        else: 
            return fh.success()
    else:
        return fh.display()

@login_required
def takeQuestionnaire(request):
    '''
    The takeQuestionnaire function allows the user to take a questionnaire
    '''
    pageHitCounter("ExcellenceTakeQuestionnaire", None, str(request.user))
    fh = FormHandle()
    fh.request = request
    fh.button = "Start"
    fh.button2 = "Cancel"
    fh.title = "Take Questionnaire"
    fh.redirectTarget = ("/excellence/showOrganisations/")
    fh.form = QuestionnaireForm(request.user)
    #Check to see if user has any teams defined in model, if make user aware
    teamList = [(orgObj.name, unicode(orgObj.name)) for orgObj in Organisation.objects.all() if (orgObj.type == "Team" and orgObj.owner == str(request.user))]
    if not teamList:
        fh.button = "Register A Team"
        fh.message = ("Sorry, You do not have a team registered. Please register a team to take a questionnaire")
    if request.method == 'POST':
        if "Cancel" in request.POST:
            fh.redirectTarget = ("/excellence/showOrganisations/")
            return fh.success()
        if "Register A Team" in request.POST:
            fh.redirectTarget = ("/excellence/addOrganisation/")
            return fh.success()
        name = request.POST.get('questionnaire_Name')
        if not name:
            fh.message = ("You must provide a Questionaire Name")
            return fh.display()
        version=request.POST.get('version')
        team=request.POST.get('organisation')
        organisation = Organisation.objects.filter(name=str(team),owner=request.user)
        if organisation:

            versionList = excellence.utils.categoryVersionManagement(version)
            logger.info("Version List Id's returned: " +str(versionList))
            try:
                organisation = request.POST.get('organisation')
                questionnairePart = 1
                try:
                    questionnaire, created = Questionnaire.objects.get_or_create(
                            questionnaire_Name=name,
                            organisation=Organisation.objects.get(name=organisation),
                            version=version)
                    
                    fh.redirectTarget = (
                                            "/excellence/questionnaire/" 
                                            +str(int(versionList[0]))+
                                            "/" +str(int(version))+
                                            "/" +str(questionnaire.id)+ 
                                            "/" +str(int(questionnairePart)) + 
                                            "/"
                                        ) 
                    logger.info("Questionnaire Table Updated with Success")
                    return fh.success()
                except Exception as e:
                    logger.error("Unable to update Questionnaire Table: " +str(e))
                    return fh.failure()
            except Exception as e:
                logger.error("Issue getting organisation Details: " +str(e))
                return fh.failure()
        else:
            fh.message = ("Sorry you don't have access to Team: '" +str(team)+ "'. Please Select a Team that you created")
            return fh.display()
    else:
        return fh.display()

@login_required
def questionnaireContinued(request,versionListFirstEntry,version,questionnaireId,part):
    '''
    The questionnaireContinued allows the user to run through the questionnaire section by section
    resulting in a questionnaire result section
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Save and Continue"
    response = "None"
    answers = Answer.objects.all()
    category = Category.objects.get(id=versionListFirstEntry)
    versionList = excellence.utils.categoryVersionManagement(version)
    categoryList = [ int(item) for item in versionList ]
    discussionForm = DiscussionItemForm()
    if request.method == 'POST':
        if not request.POST.get("feedback"):
            if Response.objects.filter(
                        questionnaire=Questionnaire.objects.get(id=questionnaireId),
                        takenBy=request.user,
                        questionnairePart=part).exists():
               logger.info("Response already exists therefore will not recreate")
            else:
                try:
                    response, created = Response.objects.get_or_create(
                            questionnaire=Questionnaire.objects.get(id=questionnaireId),
                            dateAndTimeTaken=datetime.now(),
                            takenBy=request.user,
                            questionnairePart=part)
                    logger.info("Response details for questionnaire added to Database")
                except Exception as e:
                    logger.error("Issue adding Response details for questionnaire: " +str(e))

            for key,value in request.POST.iteritems():
                if value != fh.button and "csrf" not in key:
                    responselist = request.POST.getlist(key)
                    if not responselist[0]:
                        fh.redirectTarget = str(request.path_info)
                        return fh.success()
                    answer = responselist[0]
                    comment = responselist[1]
                    commentObj = DiscussionItems.objects.create(comment=str(comment))
                    question=Question.objects.filter(question=key)
                    answer=Answer.objects.filter(value=int(answer))
                    for quest in question:
                        for answ in answer:
                            if response == "None" or QuestionAnswerResponseMapping.objects.filter(
                                    question=quest,
                                    answer=answ,
                                    comment=commentObj,
                                    response=response).exists():
                                logger.info("Question, Answer to Reponse Mapping already exists therefore will not recreate")
                            else:
                                try:
                                    mapping, created = QuestionAnswerResponseMapping.objects.get_or_create(
                                            question=quest,
                                            answer=answ,
                                            comment=commentObj,
                                            response=response)
                                    logger.info("Mapping Details Update for question, answers and response")
                                except Exception as e:
                                    logger.error("Oops Issue upading mapping Table for question, answers and response: " +str(e))
            #if current Version is not last element in the list 
            if int(versionListFirstEntry) != (categoryList[-1]):
                try:
                    #Get next element in category list
                    versionListFirstEntry = categoryList[categoryList.index(int(versionListFirstEntry))+1]
                    next = int(part) + 1 
                    fh.redirectTarget = (
                                            "/excellence/questionnaire/"
                                            +str(versionListFirstEntry)+ 
                                            "/" +str(version)+ 
                                            "/" +str(questionnaireId)+
                                            "/" +str(next)+
                                            "/"
                                        )
                    return fh.success()
                except Exception as e:
                    logger.error("Issue iterating throw the category List: " +str(e))

            try:
                logger.info("Results Section Questionnaire Complete")
                resultTuple,categoryOrdered,scoreDict,overallScore = excellence.utils.displayResults(request,questionnaireId)
                data = {'resultTuple':resultTuple,'categoryOrdered':categoryOrdered,'scoreDict':scoreDict,'overallScore':overallScore}
                return render_to_response("excellence/complete.html", data, context_instance=RequestContext(request))

            except Exception as e:
                logger.error("Issue Displaying Querntionnaire Results: " +str(e)) 
                return render(request, "excellence/complete.html")

        else:
            showPastResults(request, questionnaireId)
            return HttpResponseRedirect('/excellence/searchQuestionnaires/')
    else:
        questionnairePageDetails = excellence.utils.questionVersionManagment(versionListFirstEntry)
        for categoryName,questionList in questionnairePageDetails.items():
            return render(
                            request, 
                            "excellence/questionnaire.html" ,
                            {
                                'questionList': questionList,
                                'answers':answers,
                                'categoryName':categoryName,
                                'discussionForm':discussionForm,
                            },
                     )
@login_required
def searchQuestionnaires(request):
    '''
    The searchQuestionnaires allows a logged on user to see all questionnaire history by the user
    '''
    pageHitCounter("ExcellenceSearchQuestionnaire", None, str(request.user))
    quentionnaireDict = {}
    responses = Response.objects.values_list('questionnaire_id', flat=True).distinct()
    for response in responses:
        if Response.objects.filter(questionnaire_id=response,takenBy=request.user):
            try:
                questionnaireObj = Questionnaire.objects.get(id=response)
                responseObj = Response.objects.filter(questionnaire_id=response)
                sectionList = []
                for response in responseObj:
                    sectionList.append(int(response.questionnairePart))
                    highestSection = max(sectionList)
                    nextSection = highestSection+1
                quentionnaireDict[questionnaireObj] = (highestSection,nextSection)
                
            except Exception as e:
                logger.error("Oops ... Issue with finding response on User: " +str(e))
    return render(request, "excellence/searchResults.html" , {'quentionnaireDict': quentionnaireDict},)

@login_required
def showPastResults(request,questionnaireId):
    '''
    The showPastResults allows a logged on User to click on a Results Link on a questionnaire and see past results
    '''
    if request.method == 'POST':
        feedback = request.POST.get("feedback")
        submitEmail = request.POST.get("email")
        subject = "CI Excellence Model Feedback"
        message = "Hi CIFwk Team, \n\nFeeback has been received From User: '" +str(request.user)+ "': on the CI Excellence Model. \n\nThe Feedback is as follows:\n\n" +str(feedback)+ "\n\nHave a Great Day \nThe PDU OSS Continuous Integration Portal"
        email = config.get('CIFWK', 'cifwkDistributionList')
        send_mail(subject,message,email,[email,submitEmail], fail_silently=False)
        return HttpResponseRedirect('/excellence/searchQuestionnaires/')

    userResponse = Response.objects.filter(takenBy=request.user,questionnaire_id=int(questionnaireId))
    if userResponse:
        logger.info("Showing Results for user: " +str(request.user))
        try:
            resultTuple,categoryOrdered,scoreDict,overallScore = excellence.utils.displayResults(request,int(questionnaireId))
            return render(request, "excellence/complete.html",
                                    {
                                        'resultTuple':resultTuple,
                                        'categoryOrdered':categoryOrdered,
                                        'scoreDict':scoreDict,
                                        'overallScore':overallScore
                                    }
                         )
        except Exception as e:
                logger.error("Oops ... Cannot retrieve results: " +str(e))
                return render(request, "excellence/complete.html", {'userResponse':userResponse})

    else:
        logger.info("User: " +str(request.user)+ " Did not take this questionnaire therefore blocking Result Request")
        return render(request, "excellence/complete.html")

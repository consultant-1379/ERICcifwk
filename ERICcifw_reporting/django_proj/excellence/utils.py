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
import logging
logger = logging.getLogger(__name__)
config = CIConfig()

from datetime import datetime, timedelta
from excellence.forms import *

from django.contrib.auth.models import User, Group
from guardian.decorators import permission_required, permission_required_or_403
from guardian.conf import settings as guardian_settings
from guardian.exceptions import GuardianError
from guardian.shortcuts import assign
from guardian.shortcuts import get_perms
from guardian.core import ObjectPermissionChecker
from distutils.version import LooseVersion
import math
import csv

def questionVersionManagment(version):
    '''
    The questionVersioningManagment def splits out the questions based on versions and find last question
    if not in current version, questions will only get added if enabled is equal to 1/True
    '''
    questionList = []
    questions = Question.objects.values_list('question', flat=True).distinct()
    questions = [ str(question) for question in questions ]
    categoryObj = Category.objects.get(id=version)
    version = int(version)
    for question in questions:
        try:
            questionObj = Question.objects.get(question=question,category_id=version)
            categoryName=Category.objects.get(id=questionObj.category_id).name
            if categoryName == categoryObj.name:
                if questionObj.enable != 0:
                    questionList.append(questionObj)
            #logger.info("Question : " +str(question)+ " and version: " +str(version) + " found")
        except:
            #logger.info("Opps Question: " +str(question)+ " With Version: "
            #                    +str(version)+ " Not Found, Checking if version: " +str(version -1)+ " Exists...")
            next = version -1
            while next >> 0:
                try:
                    questionObj = Question.objects.get(question=question,category_id=next)
                    categoryName=Category.objects.get(id=questionObj.category_id).name
                    if categoryName == categoryObj.name:
                        if questionObj.enable != 0:
                            questionList.append(questionObj)
                    #logger.info("Question : " +str(question)+ " and version: " +str(next) + " found")
                    break
                except:
                    #logger.info("Opps Question: " +str(question)+ " With Version: "
                    #        +str(next)+ " Not Found, Checking if version: " +str(next -1)+ " Exists...")
                    next = next -1
    questionDict = {categoryObj.name: questionList}
    return questionDict

def categoryVersionManagement(version):
    '''
    The categoryVersionManagement def controls the versioning of the category for presenation in questionnaire
    '''
    versionList = []
    version = int(version)
    categories = Category.objects.values_list('name', flat=True).distinct()
    #logger.info("Categories Found : " +str(categories))
    for category in categories:
        try:
            categoryObj = Category.objects.get(name=category,version=version)
            versionList.append(categoryObj.id)
            #logger.info("Category Name: " +str(category)+ " with Version: " +str(version)+ " Found")
        except:
            #logger.info("Opps Category: " +str(category)+ " With Version: "
            #                    +str(version)+ " Not Found, Checking if version: " +str(version -1)+ " Exists...")
            next = version -1
            while next >> 0:
                try:
                    categoryObj = Category.objects.get(name=category,version=next)
                    versionList.append(categoryObj.id)
                    #logger.info("Category Name: " +str(category)+ " with Version: " +str(next)+ " Found")
                    break
                except:
                    #logger.info("Opps Category: " +str(category)+ " With Version: "
                    #        +str(version)+ " Not Found, Checking if version: " +str(next -1)+ " Exists...")
                    next = next -1
    #logger.info("Version List completed without any issue and returned with success")
    return versionList

def displayResults(request,OrgID):
    '''
    The displayResults build up the data that is required to be diplayed in a results page
    once a questionnaire has been complete
    '''
    try:
        resultTuple = ()
        scoreTuple = ()
        scoreDict = {}
        overallScoreList = []
        questionnaireResponse = Response.objects.filter(questionnaire=OrgID)
        for questResponseId in questionnaireResponse:
            resultId = QuestionAnswerResponseMapping.objects.filter(response_id=questResponseId)
            numberOfQuestions = 0
            totalScore = 0
            #get all question answer info for results page display
            for id in resultId:
                question = (id.question).question
                category = ((id.question).category).name
                answer = (id.answer).answer
                answerValue = int((id.answer).value)
                action = (id.question).action
                comment = id.comment.comment
                #Build up result tuple for UI display of Q's, A's and Actions
                resultTuple = resultTuple + ((category,question,answer,answerValue,action,comment),)
                #Build up total Score for Results per section UI display this will be added to scoreTuple
                totalScore = totalScore + answerValue
                numberOfQuestions = numberOfQuestions + 1
            scoreTuple = scoreTuple + ((category,numberOfQuestions,totalScore),)
        #Get all Categories from table of Results Display sectioning on UI
        categoryOrdered = Category.objects.values_list('name', flat=True).distinct()
        #Get Percentage Scores from the scoreTuple
        for score in scoreTuple:
            percentageScore = ((float(score[2])/float((score[1]*5)))*100)
            #Round up percentageScore
            percentageScore = math.ceil(percentageScore)
            #Add Category and Percentage score to Dict for Display in Results UI
            scoreDict[score[0]] = percentageScore
            #Add percentage Score to List to allow calculation of Overall Score
            overallScoreList.append(percentageScore)
        #Work out overall Score for Results UI Display
        overallScore = ((sum(overallScoreList)/500)*100)
        overallScore = math.ceil(overallScore)
        return resultTuple,categoryOrdered,scoreDict,overallScore
    except Exception as e:
        logger.error("Opps issue with result calculation" +str(e))

def ExcellenceResultsSummary(fileName):
    '''
    The ExcellenceResultsSummary function returns a summary of Excellence models Complete
    This Summary to writeen to a CSV file
    '''
    mappingObj = QuestionAnswerResponseMapping.objects.all()
    list = []
    fieldnames = ['User', 'Name', 'Organistaion','Parent Organistaion', 'Version', 'Question', 'Answer', 'Comment',]
    outputFile = open(str(fileName)+'.csv','wb')
    csvwriter = csv.DictWriter(outputFile, delimiter=',', fieldnames=fieldnames)
    csvwriter.writerow(dict((fn,fn) for fn in fieldnames))
    for map in mappingObj:
        list.append({
                        'User': str(map.response.takenBy), 
                        'Name': str(map.response.questionnaire.questionnaire_Name),
                        'Organistaion': str(map.response.questionnaire.organisation.name),
                        'Parent Organistaion': str(map.response.questionnaire.organisation.parent),
                        'Version': str(map.response.questionnaire.version),
                        'Question': str(map.question),
                        'Answer': str(map.answer.answer),
                        'Comment':str(map.comment)
                    })
    for row in list:
        csvwriter.writerow(row)
    outputFile.close()

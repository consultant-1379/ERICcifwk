from vis.models import *
from django.shortcuts import render_to_response
from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Min
from django.db import connection
from distutils.version import LooseVersion
from vis.forms import *
import json
from cireports.models import *
import logging
import re
logger = logging.getLogger(__name__)
import datetime
from django.shortcuts import render

def getRadiatorInfo(request, release):
    return HttpResponse(json.dumps(radInfo), content_type="application/json")

def showWidgets(request):
    '''
    The showWidgets function renders the showWidget html page with all widgets in database 
    '''
    widgets = Widget.objects.all()
    return render(request, "vis/showWidgets.html" , {'widgets': widgets},)

def showWidgetDefintions(request, customRender=None):
    '''
    The showWidgetDefintions renders the showWidgetDefintions html page with all widget definitions in the database 
    '''

    widgetDefinitions = WidgetDefinition.objects.all()
    #return render_to_response("vis/showWidgetDefinitions.html", {'widgetDefinitions':widgetDefinitions,'sequence':sequence},)
    if request.method == 'POST': # If the form has been submitted...
        checked=request.POST.getlist('toBeAdded')
        for widget in checked:
            widgetDefinitionObj = WidgetDefinition.objects.get(name=widget)
            widgetRenderObj = WidgetRender.objects.get(name=customRender)
            addWidgetToRenderMapping(widgetRenderObj,widgetDefinitionObj)
        return HttpResponseRedirect('/vis/showChartMappings/'+str(customRender)+'/') # Redirect after POST

    else:

        return render(request, 'vis/showWidgetDefinitions.html', {
            'widgetDefinitions':widgetDefinitions,
            'sequence':customRender,
    })

def showWidgetRender(request):
    '''
    The showWidgetRender renders the showWidgetRender html page with all widget renders in the database
    '''
    widgetRenders = WidgetRender.objects.all()
    return render(request, "vis/showWidgetRender.html", {'widgetRenders':widgetRenders},)

def showWidgetRenderToDefinitionsMappping(request):
    '''
    '''
    widgetToDefMapins = WidgetDefinitionToRenderMapping.objects.all()
    return render(request, "vis/showWidgetMappings.html", {'widgetToDefMapins':widgetToDefMapins},)

def showChartMapping(request, selected=None):
    '''
    '''
    mappings=None
    charts = WidgetRender.objects.all()
    if selected is not None:
        mappings = WidgetDefinitionToRenderMapping.objects.filter(widgetRender__name=selected)
    return render_to_response("vis/chart_mappings.html", {'charts':charts, 'selected':selected,'mappings':mappings},)

@login_required
def addWidget(request):
    '''
    The addWidget function allows the user to register a widget
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Finish..."
    fh.title = "Add Chart"
    if request.method == 'POST':
        fh.form = WidgetForm(request.POST)
        if fh.form.is_valid():
            fh.redirectTarget = "/vis/showWidgets"
            try:
                widget = fh.form.save(commit=False)
                widget.save()
                return fh.success()
            except Exception as e:
                logger.error("Unable to save " +str(widget)+ " to database: " +str(e))
                return fh.failure()
        else:
            logger.error("Form was not Valid: " +str(fh.form.errors))
            return fh.failure()
    else:
        fh.form = WidgetForm(initial={'url': "/fem/..."})
        return fh.display()

@login_required
def editWidget(request, widgetId):
    '''
    The editWidget function allows the users to edit a widget
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Update..."
    widgetObj = Widget.objects.get(id=widgetId)
    fh.title = "Edit Chart: " +str(widgetObj.name)
    if request.method == 'POST':
        fh.form = WidgetForm(request.POST, instance=widgetObj)
        if fh.form.is_valid():
            fh.redirectTarget = "/vis/showWidgets"
            try:
                widgetObj.name = fh.form.cleaned_data['name']
                widgetObj.description = fh.form.cleaned_data['description']
                widgetObj.type = fh.form.cleaned_data['type']
                widgetObj.url = fh.form.cleaned_data['url']
                widgetObj.save(force_update=True)
                return fh.success()
            except Exception as e:
                logger.error("The was an issue with the form: " +str(e)) 
                return fh.failure()
        else:
            return fh.failure()
    else:
        fh.form = WidgetForm(initial =
                            {
                                'name':widgetObj.name,
                                'description':widgetObj.description,
                                'type':widgetObj.type,
                                'url':widgetObj.url,
                            })
        return fh.display()

@login_required
def deleteWidget(request, widgetId):
    '''
    The deleteWidget function allows users to delete a widget
    '''
    widgetObj = Widget.objects.get(id=widgetId)
    try:
        widgetObj.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/vis/showWidgets")
    except Exception as e:
        logger.error("Unable to delete Widget: " + str(widgetObj.name) + " exception thrown: " + str(e))
        return HttpResponseRedirect("/vis/showWidgets")
@login_required
def addWidgetDefinition(request, widgetId):
    '''
    The addWidgetDefinition is used to define a widget definition
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Finish..."
    widgetObj = Widget.objects.get(id=widgetId) 
    fh.title = "Add Chart Configuration for Chart " +str(widgetObj.name)
    if request.method == 'POST':
        fh.form = WidgetDefinitionForm(request.POST)
        if fh.form.is_valid():
            fh.redirectTarget = "/vis/showWidgetDefinitions/"
            try:
                widgetDefintion = fh.form.save(commit=False)
                widgetDefintion.widget = widgetObj
                widgetDefintion.granularity = widgetDefintion.granularity.lower()
                if widgetDefintion.refresh < 10:
                    fh.message = "Unable to save " +str(widgetDefintion.name)+ " to database as refresh time needs to be more than 10 Seconds: " 
                    return fh.display()
                widgetDefintion.save()
                return fh.success()
            except Exception as e:
                logger.error("Unable to save " +str(widgetDefintion.name)+ " to database: " +str(e))
                return fh.failure()
        else:
            logger.error("Form was not Valid: " +str(fh.form.errors))
            return fh.failure()
    else:
        fh.form = WidgetDefinitionForm(initial = 
                        {
                            'refresh': 60, 
                        })
        return fh.display()
@login_required
def editWidgetDefinition(request, widgetDefinitionId):
    '''
    The editWidgetDefinition allows users to edit a widget definition
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Update..."
    widgetDefinitionObj = WidgetDefinition.objects.get(id=widgetDefinitionId)
    fh.title = "Edit Chart Configuration: " +str(widgetDefinitionObj.name)
    if request.method == 'POST':
        fh.form = WidgetDefinitionForm(request.POST, instance=widgetDefinitionObj)
        if fh.form.is_valid():
            fh.redirectTarget = "/vis/showWidgetDefinitions/"
            try:
                widgetDefinitionObj.name = fh.form.cleaned_data['name']
                widgetDefinitionObj.description = fh.form.cleaned_data['description']
                widgetDefinitionObj.view_id = fh.form.cleaned_data['view']
                widgetDefinitionObj.refresh = fh.form.cleaned_data['refresh']
                if widgetDefinitionObj.refresh < 10:
                    fh.message = "Unable to save " +str(widgetDefinitionObj.name)+ " to database as refresh time needs to be more than 10 Seconds: "
                    return fh.display()
                widgetDefinitionObj.granularity = fh.form.cleaned_data['granularity'] 
                widgetDefinitionObj.save(force_update=True)
                return fh.success()
            except Exception as e:
                logger.error("The was an issue with the form: " +str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        fh.form = WidgetDefinitionForm(initial =
                    {
                        'name':widgetDefinitionObj.name,
                        'description':widgetDefinitionObj.description,
                        'widget': widgetDefinitionObj.widget_id,
                        'view': widgetDefinitionObj.view_id,
                        'refresh': widgetDefinitionObj.refresh,
                        'granularity':widgetDefinitionObj.granularity,
                    })
        return fh.display()

@login_required
def deleteWidgetDefinition(request, widgetDefinitionId):
    '''
    The deleteWidgetDefinition function allows users to delete a widget definition
    '''
    widgetDefinitionObj = WidgetDefinition.objects.get(id=widgetDefinitionId)
    try:
        widgetDefinitionObj.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/vis/showWidgetDefinitions/")
    except Exception as e:
        logger.error("Unable to delete Chart Configuration: " + str(widgetDefinitionObj.name) + " exception thrown: " + str(e))
        return HttpResponseRedirect("/vis/showWidgetDefinitions/")

def getWidgetRenders():
    '''
    The getWidgetRenders function gets all the widget Renders in the database whih will be diplay on the add Widget Render Form
    '''
    widgetRenderList = ()
    #widgetRenderObj = WidgetRender.objects.all()
    widgetRenderObj = WidgetRender.objects.all() 
    if WidgetRender.objects.all().exists():
        #Build up a widgetRenderList in a choices format for display on the add Widget Rendor form on Existing Renders
        for widgetRender in widgetRenderObj:
            widgetRenderList = widgetRenderList + ("[\""+str(widgetRender.name)+"\", \""+str(widgetRender.name)+"\"]",)
    newRender = "New Chart Sequence"
    widgetRenderList = widgetRenderList + ("[\""+str(newRender)+"\", \""+str(newRender)+"\"]",)
    widgetRenderList = re.sub(r'\'', '', str(widgetRenderList))
    widgetRenderList = eval(widgetRenderList)   
    return widgetRenderList

@login_required
def WidgetRenders(request, Id, option, customrender=None):
    '''
    The WidgetRenders function handles both adding and editing Widget Renders and associating the render to a definition
    Also this function allows the widget Render to select an existing render or create a new render
    The WidgetRenders function calls the addWidgetToRenderMapping functions to add the mapping information from 
    definition to render:w!
    '''
    fh = FormHandle()
    fh.request = request
    if request.method == 'POST': 
        fh.form = WidgetRenderForm(request.POST)
        name = request.POST.get('name')
        description = request.POST.get('description')
        #As the form.is.valid function is not been called here there is a check for form validition below
        if name and description:
            logger.info(str(name) + " and " +str(description)+ " Fields are filled in continue...")
        else:
            #Calls the getWidgetRenders function, this allows the drop down on the UI to be populated with existing Renders for selection
            widgetRenderList = getWidgetRenders()
            fh.form = WidgetRenderForm(widgetRenderList)
            fh.message = ("Form is invalid please ensure all fields are filled in:")
            return fh.display()  
        if customrender is not None:
            fh.redirectTarget = "/vis/showChartMappings/"+str(customrender)
        else:
            fh.redirectTarget = "/vis/showChartMappings/"
        try:
            if option == "add":
                try:
                    if Id == "new":
                        widgetRender, widgetRenderCreate = WidgetRender.objects.get_or_create(name=name, description=description )
                    else:
                        widgetDefinitionObj = WidgetDefinition.objects.get(id=Id)
                        widgetRenderObj = WidgetRender.objects.get(name=customrender)
                        addWidgetToRenderMapping(widgetRenderObj,widgetDefinitionObj)
                    return fh.success()
                except Exception as e:
                        logger.error(str(fh.form.errors))
                        return fh.failure()

                #Below the get or create option is selected on the object whisch write the info to the Widget rendor table, return the Truw if its a success
            else: 
                try:
                    widgetRenderObj = WidgetRender.objects.get(name=customrender)
                    widgetRenderObj.name = name
                    widgetRenderObj.save(force_update=True)
                    fh.redirectTarget = "/vis/showChartMappings/"+str(widgetRenderObj.name)


                    return fh.success()
                except Exception as e:
                    logger.error(str(e))
                    return fh.failure()
        except Exception as e:
                logger.error(str(e))
                if Id == "new":
                    widgetRenderList = (["New Chart Sequence","New Chart Sequence"]),
                elif customrender is not None:
                    widgetRenderList = ([str(customrender), str(customrender)]),
                else:
                    widgetRenderList = getWidgetRenders()
                fh.form = WidgetRenderForm(widgetRenderList)
                fh.message = ("There was an issue adding Chart Sequence: "
                    + str(name) + ". Please Try again " + str(e))
                return fh.display()
    else:
        if Id == "new":
            widgetRenderList = (["New Chart Sequence","New Chart Sequence"]),
        elif customrender is not None:
            widgetRenderList = ([str(customrender), str(customrender)]),
        else:
            widgetRenderList = getWidgetRenders()
        if option == "add":
            fh.button = "Finish..."
            if Id != "new": 
                widgetDefinitionObj = WidgetDefinition.objects.get(id=Id)
                fh.title = "Add Chart Sequence for Chart Configuration " +str(widgetDefinitionObj.name)
            else:
                fh.title = "Add New Chart Sequence for Chart Configuration "
            fh.form = WidgetRenderForm(widgetRenderList) 
        else:
            if customrender is not None:
                widgetRenderList = ([str(customrender), str(customrender)]),
            fh.button = "Update..."
            widgetRenderObj = WidgetRender.objects.get(id=Id)
            fh.title = "Update Chart Sequence for Chart Configuration " +str(widgetRenderObj.name)
            fh.form = WidgetRenderForm(widgetRenderList,initial =
                    {
                        'name':widgetRenderObj.name,
                        'description':widgetRenderObj.description,
                    })
        return fh.display()

@login_required
def deleteWidgetRender(request, widgetRenderId):
    '''
    The deleteWidgetRender function allow a user to delete a widget
    '''
    widgetRenderObj = WidgetRender.objects.get(id=widgetRenderId)

    try:
        associated = WidgetRender.objects.filter(name=widgetRenderObj.name)
        associated.delete()
        widgetRenderObj.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/vis/showChartMappings/")
    except Exception as e:
        logger.error("Unable to delete Chart Sequence: " + str(widgetRenderObj.name) + " exception thrown: " + str(e))
        return HttpResponseRedirect("/vis/showChartMappings/")


def addWidgetToRenderMapping(widgetRenderObj,WidgetDefinitionObj):
    ''' 
    The addWidgetToRenderMapping function populates the widget definition to render table
    '''
    model = WidgetDefinitionToRenderMapping()
    model.widgetDefinition = WidgetDefinitionObj
    model.widgetRender = widgetRenderObj 
    model.save()

@login_required
def deleteMapping(request, mappingId, customRender):
    '''
    The deleteMapping function allows users to delete a widget mapping
    '''
    widgetMappingObject = WidgetDefinitionToRenderMapping.objects.get(id=mappingId)
    try:
        widgetMappingObject.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/vis/showChartMappings/"+str(customRender)+"/")
    except Exception as e:
        logger.error("Unable to delete Chart Mapping: " + str(widgetMappingObject.id) + " exception thrown: " + str(e))
        return HttpResponseRedirect("/vis/showChartMappings/"+str(customRender)+"/")

@login_required
def editMapping(request, mappingId):
    '''
    The editWidget function allows the users to edit a widget
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Update..."
    mappingObject = WidgetDefinitionToRenderMapping.objects.get(id=mappingId)
    fh.title = "Edit Chart Configuration to Chart Mapping: " +str(mappingObject.id)
    if request.method == 'POST':
        fh.form = WidgetMappingForm(request.POST, instance=mappingObject)
        if fh.form.is_valid():
            fh.redirectTarget = "/vis/showWidgetMappings/"
            try:
                mappingObject.widgetDefinition = fh.form.cleaned_data['widgetDefinition']
                mappingObject.widgetRender = fh.form.cleaned_data['widgetRender']
                mappingObject.save(force_update=True)
                return fh.success()
            except Exception as e:
                logger.error("The was an issue with the form: " +str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        fh.form = WidgetMappingForm(initial =
                            {
                                'widgetDefinition':mappingObject.widgetDefinition,
                                'widgetRender':mappingObject.widgetRender,
                            })
        return fh.display()

def radiatorCustomView(request, customView=None):
    '''
    render custom view
    '''
    allDrops = list(Drop.objects.all())
    allDrops.sort(key=lambda drop:LooseVersion(drop.name), reverse=True)
    drop = allDrops[0].id
    drop = Drop.objects.get(id=drop)
    if WidgetRender.objects.filter(name=customView).exists():
        return render(request, "cireports/radiator_base_custom.html", {
            "customView":  customView
            }
        )
    else:
        return render(request, "cireports/radiator_base_not_found.html")

def radiatorCustomViewJson(request, customView=None):
    '''
    Return information on custom view in json format
    '''
    allDrops = list(Drop.objects.all())
    allDrops.sort(key=lambda drop:LooseVersion(drop.name), reverse=True)
    drop = allDrops[0].id
    drop = Drop.objects.get(id=drop)
    data = WidgetDefinitionToRenderMapping.objects.filter(widgetRender__name=customView)
    dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None
    jsonReturn =[] 
    for widgets in data:
        jsonReturnTmp = [
                {
                    "name": widgets.widgetDefinition.name,
                    "type": widgets.widgetDefinition.widget.type,
                    "url":  widgets.widgetDefinition.widget.url,
                    "refresh": widgets.widgetDefinition.refresh,
                    "granularity": widgets.widgetDefinition.granularity,
                    "view":widgets.widgetDefinition.view.name,
                    "job": "",
                },
                ]
        jsonReturn = jsonReturn + jsonReturnTmp

    return HttpResponse(json.dumps(jsonReturn, default=dthandler), content_type="application/json")



from django.shortcuts import render
from django.views.generic import TemplateView
from cireports.models import *
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required

class BaselineView(TemplateView):
    template_name = "angularVis/baseline.html"

@login_required
def getLatestENMDrop(self):
    field = ("name",)
    latestDrop = Drop.objects.only(field).values(*field).filter(release__product__name='ENM', correctionalDrop=False).exclude(release__name__icontains="test").latest("id")
    return HttpResponseRedirect("/visualisation/baseline/"+latestDrop['name'])

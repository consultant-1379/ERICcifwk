from cireports.models import *

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

def deliver(request):
    """
    Present an admin interface purely for delivering a package to a baseline
    """
    return render(request, "cireports/admin/deliver.html",
            {"package_list" : Package.objects.all()},
    )

deliver = staff_member_required(deliver)

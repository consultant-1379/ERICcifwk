from django.core.management.base import BaseCommand
from cireports.models import Package

class Command(BaseCommand):
    help = "Update Packages that have the wrong testware flag"

    def handle(self, *args, **options):
        packageObj = Package.objects.filter(testware=False)
        for package in packageObj:
            if "ERICTAF" or "ERICTW" in package.name:
                package.testware = True
                package.save(force_update=True)


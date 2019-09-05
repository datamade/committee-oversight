# Based on the Wagtail demo:
# https://github.com/wagtail/bakerydemo/blob/master/bakerydemo/base/management/commands/load_initial_data.py
import os
from distutils.dir_util import copy_tree

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command

from wagtail.core.models import Site, Page


class Command(BaseCommand):
    def handle(self, **options):
        project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
        fixtures_dir = os.path.join(project_dir, 'fixtures')
        initial_data_file = os.path.join(fixtures_dir, 'initial_cms_content.json')

        # Wagtail creates default Site and Page instances during install, but we already have
        # them in the data load. Remove the auto-generated ones.
        if Site.objects.filter(hostname='localhost').exists():
            Site.objects.get(hostname='localhost').delete()
        if Page.objects.filter(title='Welcome to your new Wagtail site!').exists():
            Page.objects.get(title='Welcome to your new Wagtail site!').delete()

        call_command('loaddata', initial_data_file, verbosity=0)

        print("Initial data loaded!")

        initial_image_src = os.path.join(fixtures_dir, 'initial_images')
        initial_image_dest = os.path.join(settings.MEDIA_ROOT, 'original_images')

        copy_tree(initial_image_src, initial_image_dest)

        print("Initial images populated!")

# Based on the Wagtail demo:
# https://github.com/wagtail/bakerydemo/blob/master/bakerydemo/base/management/commands/load_initial_data.py
import os
from distutils.dir_util import copy_tree

from django.conf import settings
from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.exceptions import ObjectDoesNotExist

from wagtail.core.models import Site, Page, PageRevision
from wagtail.images.models import Image


class Command(BaseCommand):
    def handle(self, **options):
        project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
        fixtures_dir = os.path.join(project_dir, 'fixtures')
        initial_data_file = os.path.join(fixtures_dir, 'initial_cms_content.json')
        initial_data_file_custom_pages = os.path.join(fixtures_dir, 'initial_cms_content_custom_pages.json')

        # Delete existing Wagtail models
        try:
            Site.objects.all().delete()
            Page.objects.all().delete()
            PageRevision.objects.all().delete()
            Image.objects.all().delete()

            for Model in apps.get_app_config('committeeoversightapp').get_models():
                if getattr(Model, 'reset_on_load', False):
                    Model.objects.all().delete()

        except ObjectDoesNotExist as e:
            print(e)



        call_command('loaddata', initial_data_file, verbosity=0)
        call_command('loaddata', initial_data_file_custom_pages, verbosity=0)

        print("Initial data loaded!")

        initial_image_src = os.path.join(fixtures_dir, 'initial_images')
        initial_image_dest = os.path.join(settings.MEDIA_ROOT, 'original_images')

        copy_tree(initial_image_src, initial_image_dest)

        print("Initial images populated!")

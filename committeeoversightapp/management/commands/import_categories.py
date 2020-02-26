import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection

CATEGORIES_ML_CSV = 'data/final/categories_ml.csv'
CATEGORIES_EDITED_CSV = 'data/final/categories_edited.csv'

class Command(BaseCommand):
    help = "Import manually entered hearing categories"

    def handle(self, *args, **options):
        file_names = [CATEGORIES_ML_CSV, CATEGORIES_EDITED_CSV]

        for file_name in file_names:
            self.stdout.write('Loading in {}...'.format(file_name))

            with open(file_name, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    pass

            self.stdout.write(self.style.SUCCESS('{} loaded!'.format(file_name)))

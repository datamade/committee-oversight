import csv

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction, connection

from committeeoversightapp.models import HearingEvent, HearingCategoryType, HearingCategory

CATEGORIES_EDITED_CSV = 'data/final/categories_edited.csv'
CATEGORIES_ML_CSV = 'data/final/categories_ml.csv'

class Command(BaseCommand):
    help = "Import manually entered hearing categories"

    def handle(self, *args, **options):
        file_names = [CATEGORIES_EDITED_CSV, CATEGORIES_ML_CSV]

        for file_name in file_names:
            self.stdout.write('Loading in {}...'.format(file_name))

            with open(file_name, 'r') as csvfile:
                no_match = []
                matches = 0

                reader = csv.DictReader(csvfile)
                for row in reader:
                    name = self.clean_encoding(row['NAME'])
                    try:
                        hearing = HearingEvent.objects.get(
                            start_date=row['DATE'],
                            name=name
                        )

                        category = HearingCategoryType.objects.get(
                            name=row['CATEGORY']
                        )

                        hearing_category, created = HearingCategory.objects.get_or_create(
                            event=hearing
                        )

                        hearing_category.category = category
                        hearing_category.save()

                        matches += 1

                    except ObjectDoesNotExist:
                        no_match += [row['DATE'] + ',' + row['NAME']]

            self.stdout.write(
                self.style.SUCCESS(
                    '{file_name} loaded! \
                    \n{matches} hearings matched. \
                    \n{no_matches_len} with no matches.'.format(
                    file_name=file_name,
                    matches=matches,
                    no_matches_len=len(no_match),
                ))
            )

            with open('no_category_match.csv', 'a') as f:
                for row in no_match:
                    f.write(row + '\n')

    def clean_encoding(self, name):
        return name \
            .replace('â€“', '–') \
            .replace('â€™', '’') \
            .replace('â€\x9d', '”') \
            .replace('â€œ', '“') \
            .replace('â€˜', '‘') \
            .replace('â€”', '—')

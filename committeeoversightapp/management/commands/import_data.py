import os
import csv

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import IntegrityError

from opencivicdata.legislative.models import Event, EventSource
from committeeoversightapp.models import HearingCategory

jurisdiction_id = 'ocd-jurisdiction/country:us/legislature'
bad_rows = []

class Command(BaseCommand):
    help = "Import Lugar spreadsheets data"

    def handle(self, *args, **options):

        # Create hearings
        self.stdout.write(str(datetime.now()) + ': Creating database entries for the House...')
        self.add_house_hearings()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': House hearings imported successfully!'))


        self.stdout.write(str(datetime.now()) + ': Creating database entries for the Senate...')
        self.add_senate_hearings()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Senate hearings imported successfully!'))

        # Write bad category rows to file
        with open('bad_rows.txt', 'a') as f:
            for row in bad_rows:
                f.write(row + '\n')

    def add_house_hearings(self):
        with open('data/final/house.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            row_count = 2

            for row in reader:

                source = row[0]
                start_date = row[3]
                name = row[4]
                classification = row[7]
                committees = [row[8], row[9], row[10], row[11]]
                category = row[12]

                if name:
                    # get or create hearing
                    event, created = Event.objects.get_or_create(jurisdiction_id = jurisdiction_id,
                                    name = name,
                                    start_date = start_date,
                                    classification = classification)

                    if created:
                        event.save()

                        # save committee data (TK)
                        # for committee in committees:

                        # save event source
                        source = EventSource(event=event, note="spreadsheet", url=source)
                        source.save()

                        # save category data
                        try:
                            category = HearingCategory(event=event, category_id=category)
                            category.save()
                        except IntegrityError:
                            bad_rows.append("Unrecognized category on House row " + str(row_count) + ": " + event.name)

                    row_count += 1

    def add_senate_hearings(self):
        with open('data/final/senate.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            row_count = 2

            for row in reader:

                source = row[0]
                start_date = row[2]
                name = row[3]
                classification = row[6]
                committees = [row[7], row[8]]
                category = row[9]

                if name:
                    # get or create hearing
                    event, created = Event.objects.get_or_create(jurisdiction_id = jurisdiction_id,
                                    name = name,
                                    start_date = start_date,
                                    classification = classification)
                    if created:
                        event.save()

                        # save committee data (TK)
                        # for committee in committees:

                        # save event source
                        source = EventSource(event=event, note="spreadsheet", url=source)
                        source.save()

                        # save category data
                        try:
                            category = HearingCategory(event=event, category_id=category)
                            category.save()
                        except IntegrityError:
                            bad_rows.append("Unrecognized category on Senate row " + str(row_count) + ": " + event.name)

                    row_count += 1

import os
import csv

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q

from opencivicdata.core.models import Organization, OrganizationName
from opencivicdata.legislative.models import Event, EventSource
from committeeoversightapp.models import HearingCategory, Committee

jurisdiction_id = 'ocd-jurisdiction/country:us/legislature'
bad_rows = []

class Command(BaseCommand):
    help = "Import Lugar spreadsheets data"

    def handle(self, *args, **options):

        # Create commmittees from key
        self.stdout.write(str(datetime.now()) + ': Creating House committees from key...')
        self.add_house_committees()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': House committees imported successfully!'))

        self.stdout.write(str(datetime.now()) + ': Creating Senate committees from key...')
        self.add_senate_committees()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Senate committees imported successfully!'))

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

    def add_house_committees(self):
        house = Organization.objects.get(name="United States House of Representatives")

        with open('data/final/house_committees.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['Committees and Subcommittees']
                committee_name = row['b']
                classification = "committee"

                if committee_key:
                    try:
                        if committee_name == "Full Committee":
                            pass
                        else:
                            if len(committee_key) == 3:
                                parent = house

                                organization = Organization.objects.filter(Q(name__icontains=committee_name, parent=parent, classification=classification) |
                                            Q(other_names__name__icontains=committee_name, parent=parent, classification=classification))[0]

                                parent = organization

                            else:
                                organization = Organization.objects.filter(Q(name__icontains=committee_name, parent=parent, classification=classification) |
                                            Q(other_names__name__icontains=committee_name, parent=parent, classification=classification))[0]

                            new_committee, _ = Committee.objects.get_or_create(lugar_id=committee_key, organization=organization)
                            self.stdout.write(self.style.SUCCESS("Successfully created " + committee_name + " as " + new_committee.organization.name + " with parent " + parent.name))
                    except IndexError:
                        self.stdout.write(self.style.ERROR("No committee entry found in database for " + committee_name))
                        bad_rows.append("No House committee entry found in database for " + committee_name + " (" + committee_key + ")" )

    def add_senate_committees(self):
        senate = Organization.objects.get(name="United States Senate")

        with open('data/final/senate_committees.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['Committees']
                committee_name = row['b']
                classification = "committee"

                try:
                    organization = Organization.objects.filter(Q(name__icontains=committee_name, parent=senate, classification=classification) |
                                Q(other_names__name__icontains=committee_name, parent=senate, classification=classification))[0]

                    new_committee, _ = Committee.objects.get_or_create(lugar_id=committee_key, organization=organization)

                except IndexError:
                    self.stdout.write(self.style.ERROR("No committee entry found in database for " + committee_name))
                    bad_rows.append("No Senate committee entry found in database for " + committee_name + " (" + committee_key + ")" )

    def add_house_hearings(self):
        with open('data/final/house.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 2

            for row in reader:

                source = row['source']
                start_date = row['Date']
                name = row['Hearing/Report']
                classification = row['Type']
                committees = [row['Committee1'], row['Committee1'], row['Subcommittee'], row['Subcommittee2']]
                category = row['Category1']

                if name:
                    # get or create hearing
                    event, created = Event.objects.get_or_create(jurisdiction_id = jurisdiction_id,
                                    name = name,
                                    start_date = start_date,
                                    classification = classification)

                    if created:

                        # save committee data
                        # for committee_key in committees:
                        #     name = Committee.objects.get(lugar_id=committee_key).organization.name
                        #     organization = Committee.objects.get(lugar_id=committee_key).organization
                        #     entity_type = "organization"
                        #     committee = EventParticipant(name=name, event=event, organization=organization, entity_type=entity_type)
                        #     committee.save()

                        # save event source
                        source = EventSource(event=event, note="spreadsheet", url=source)
                        source.save()

                        # save category data
                        try:
                            category = HearingCategory(event=event, category_id=category)
                            category.save()
                        except IntegrityError:
                            self.stdout.write(self.style.ERROR("Unrecognized category on House row " + str(row_count) + ": " + event.name))
                            bad_rows.append("Unrecognized category on House row " + str(row_count) + ": " + event.name)

                    row_count += 1

    def add_senate_hearings(self):
        with open('data/final/senate.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 2

            for row in reader:

                source = row['source']
                start_date = row['Date']
                name = row['Hearing/Report']
                classification = row['Type']
                committees = [row['Committee1'], row['Committee2']]
                category = row['Category1']

                if name:
                    # get or create hearing
                    event, created = Event.objects.get_or_create(jurisdiction_id = jurisdiction_id,
                                    name = name,
                                    start_date = start_date,
                                    classification = classification)
                    if created:

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
                            self.stdout.write(self.style.ERROR("Unrecognized category on House row " + str(row_count) + ": " + event.name))
                            bad_rows.append("Unrecognized category on Senate row " + str(row_count) + ": " + event.name)

                    row_count += 1

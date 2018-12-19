import os
import csv

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q

from opencivicdata.core.models import Organization, OrganizationName
from opencivicdata.legislative.models import Event, EventSource, EventParticipant
from committeeoversightapp.models import HearingCategory, Committee

jurisdiction_id = 'ocd-jurisdiction/country:us/legislature'
bad_rows = []

def new_committee(committee_key, event, row_count):
    try:
        name = Committee.objects.get(lugar_id=committee_key).organization.name
        organization = Committee.objects.get(lugar_id=committee_key).organization
        entity_type = "organization"
        committee, created = EventParticipant.objects.get_or_create(name=name, event=event, organization=organization, entity_type=entity_type)

    except (ObjectDoesNotExist, AttributeError, ValueError) as e:
        bad_rows.append("Row " + str(row_count) + ": Bad committee key " + committee_key)


class Command(BaseCommand):
    help = "Import Lugar spreadsheets data"

    def handle(self, *args, **options):

        # Create commmittees from key
        self.stdout.write(str(datetime.now()) + ': Creating House committees from key...')
        bad_rows.append("House Committees\n")
        self.add_house_committees()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': House committees imported successfully!'))

        self.stdout.write(str(datetime.now()) + ': Creating Senate committees from key...')
        bad_rows.append("\nSenate Committees\n")
        self.add_senate_committees()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Senate committees imported successfully!'))

        # Create hearings
        self.stdout.write(str(datetime.now()) + ': Creating database entries for the House...')
        bad_rows.append("\nHouse Hearings\n")
        self.add_house_hearings()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': House hearings imported successfully!'))


        self.stdout.write(str(datetime.now()) + ': Creating database entries for the Senate...')
        bad_rows.append("\nSenate Hearings\n")
        self.add_senate_hearings()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Senate hearings imported successfully!'))

        # Write bad category rows to file
        with open('bad_rows.txt', 'a') as f:
            for row in bad_rows:
                f.write(row + '\n')

    def add_house_committees(self):
        house = Organization.objects.get(name="United States House of Representatives")

        with open('data/final/house_committees_edited.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['Committees and Subcommittees']
                committee_name = row['b']
                classification = "committee"

                if committee_key:
                    try:
                        # ignore subcommittees that are actually a full committee meeting
                        if committee_name == "Full Committee" or committee_name == "Full Commission":
                            pass
                        else:
                            # full committees are three digits
                            if len(committee_key) == 3:
                                parent = house

                                organization = Organization.objects.filter(Q(name__icontains=committee_name, parent=parent, classification=classification) |
                                            Q(other_names__name__icontains=committee_name, parent=parent, classification=classification))[0]

                                parent = organization

                            else:
                                organization = Organization.objects.filter(Q(name__icontains=committee_name, parent=parent, classification=classification) |
                                            Q(other_names__name__icontains=committee_name, parent=parent, classification=classification))[0]

                            new_committee, _ = Committee.objects.get_or_create(lugar_id=committee_key, lugar_name=committee_name, organization=organization)
                    except IndexError:
                        new_committee, _ = Committee.objects.get_or_create(lugar_id=committee_key, lugar_name=committee_name)
                        bad_rows.append("Not recognized: " + committee_key + ", " + committee_name)

    def add_senate_committees(self):
        senate = Organization.objects.get(name="United States Senate")

        with open('data/final/senate_committees_edited.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['Committees']
                committee_name = row['b']
                classification = "committee"

                try:
                    organization = Organization.objects.filter(Q(name__icontains=committee_name, parent=senate, classification=classification) |
                                Q(other_names__name__icontains=committee_name, parent=senate, classification=classification))[0]

                    new_committee, _ = Committee.objects.get_or_create(lugar_id=committee_key, lugar_name=committee_name, organization=organization)

                except IndexError:
                    new_committee, _ = Committee.objects.get_or_create(lugar_id=committee_key, lugar_name=committee_name)
                    bad_rows.append("Not recognized: " + committee_key + ", " + committee_name)

    def add_house_hearings(self):
        with open('data/final/house.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 2

            for row in reader:

                source = row['source']
                start_date = row['Date'].split('T', 1)[0]
                name = row['Hearing/Report']
                classification = row['Type']
                committee1 = row['Committee1']
                committee2 = row['Committee2']
                subcommittee1 = row['Subcommittee']
                subcommittee2 = row['Subcommittee2']
                category = row['Category1']

                if name:
                    # get or create hearing
                    event, created = Event.objects.get_or_create(jurisdiction_id = jurisdiction_id,
                                    name = name,
                                    start_date = start_date,
                                    classification = classification)

                    # save committee1 data
                    if committee1 and not subcommittee1:
                        new_committee(committee1, event, row_count)
                    elif subcommittee1 == (committee1 + str(0)):
                        new_committee(committee1, event, row_count)
                    elif committee1:
                        new_committee(subcommittee1, event, row_count)

                    # save committee2 data
                    if committee2 and not subcommittee2:
                        new_committee(committee2, event, row_count)
                    elif committee2 and subcommittee2 == (committee2 + str(0)):
                        new_committee(committee2, event, row_count)
                    elif committee2:
                        new_committee(subcommittee2, event, row_count)

                    if created:

                        # save event source
                        source = EventSource(event=event, note="spreadsheet", url=source)
                        source.save()

                        # save category data
                        try:
                            category = HearingCategory(event=event, category_id=category)
                            category.save()
                        except IntegrityError:
                            bad_rows.append("Row " + str(row_count) + ": Unrecognized category " + category.category_id + " on " + event.name)

                    row_count += 1

    def add_senate_hearings(self):
        with open('data/final/senate.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 2

            for row in reader:

                source = row['source']
                start_date = row['Date'].split('T', 1)[0]
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


                    # save committee data
                    for committee in committees:
                        if committee:
                            new_committee(committee, event, row_count)

                    if created:
                        # save event source
                        source = EventSource(event=event, note="spreadsheet", url=source)
                        source.save()

                        # save category data
                        try:
                            category = HearingCategory(event=event, category_id=category)
                            category.save()
                        except IntegrityError:
                            bad_rows.append("Row " + str(row_count) + ": Unrecognized category " + category.category_id + " on " + event.name)

                    row_count += 1

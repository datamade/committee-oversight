import os
import csv
import re
import uuid

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q

from opencivicdata.core.models import Organization, OrganizationName
from opencivicdata.legislative.models import Event, EventSource, EventParticipant
from committeeoversightapp.models import HearingCategory, Committee

class Command(BaseCommand):
    help = "Import Lugar spreadsheets data"

    def handle(self, *args, **options):
        self.bad_rows = []
        self.jurisdiction_id = 'ocd-jurisdiction/country:us/legislature'
        self.match_count = 0

        # Create commmittees from key
        self.stdout.write(str(datetime.now()) + ': Creating House committees from key...')
        self.bad_rows.append("House Committees\n")
        self.add_house_committees()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': House committees imported successfully!'))

        self.stdout.write(str(datetime.now()) + ': Creating Senate committees from key...')
        self.bad_rows.append("\nSenate Committees\n")
        self.add_senate_committees()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Senate committees imported successfully!'))

        # Create hearings
        self.stdout.write(str(datetime.now()) + ': Creating database entries for the House...')
        # self.bad_rows.append("\nHouse Hearings\n")
        # self.add_house_hearings()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': House hearings imported successfully!'))

        self.stdout.write(str(datetime.now()) + ': Creating database entries for the Senate...')
        self.bad_rows.append("\nSenate Hearings\n")
        self.add_senate_hearings()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Senate hearings imported successfully!'))

        # Write bad category rows to file
        with open('bad_rows.txt', 'a') as f:
            for row in self.bad_rows:
                f.write(row + '\n')

        # Print match count
        self.stdout.write("Matches: " + str(self.match_count))

    def add_house_committees(self):
        house = Organization.objects.get(name="United States House of Representatives")

        with open('data/final/house_committees_edited.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['Committees and Subcommittees']
                committee_name = row['b']
                classification = "committee"

                if committee_key:
                    # ignore subcommittees that are actually a full committee meeting
                    if committee_name == "Full Committee" or committee_name == "Full Commission":
                        pass
                    else:
                        # full committees have three digit lugar keys, eg 201 "Aging"
                        if len(committee_key) == 3:
                            parent = house
                            organization = self.get_committee(committee_name, parent, committee_key)
                            parent = organization
                        else:
                            organization = self.get_committee(committee_name, parent, committee_key)
                        new_event_participant, _ = Committee.objects.get_or_create(lugar_id=committee_key, lugar_name=committee_name, organization=organization)

    def add_senate_committees(self):
        senate = Organization.objects.get(name="United States Senate")

        with open('data/final/senate_committees_edited.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['Committees']
                committee_name = row['b']
                classification = "committee"

                organization = self.get_committee(committee_name, senate, committee_key)
                new_event_participant, _ = Committee.objects.get_or_create(lugar_id=committee_key, lugar_name=committee_name, organization=organization)

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
                    event, created = Event.objects.get_or_create(jurisdiction_id = self.jurisdiction_id,
                                    name = name,
                                    start_date = start_date,
                                    classification = classification)

                    # save committee1 data
                    if committee1 and not subcommittee1:
                        self.new_event_participant(committee1, event, row_count)
                    elif subcommittee1 == (committee1 + str(0)):
                        self.new_event_participant(committee1, event, row_count)
                    elif committee1:
                        self.new_event_participant(subcommittee1, event, row_count)

                    # save committee2 data
                    if committee2 and not subcommittee2:
                        self.new_event_participant(committee2, event, row_count)
                    elif committee2 and subcommittee2 == (committee2 + str(0)):
                        self.new_event_participant(committee2, event, row_count)
                    elif committee2:
                        self.new_event_participant(subcommittee2, event, row_count)

                    if created:

                        # save event source
                        source = EventSource.objects.create(event=event, note="spreadsheet", url=source)

                        # save category data
                        try:
                            hearing_category = HearingCategory.objects.create(event=event, category_id=category)
                        except IntegrityError:
                            self.bad_rows.append("Row " + str(row_count) + ": Unrecognized category " + category + " on " + event.name)

                    row_count += 1

    def add_senate_hearings(self):
        with open('data/final/senate.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 2

            for row in reader:

                matched = False

                name = row['Hearing/Report']
                start_date = row['Date'].split('T', 1)[0]

                committees = [row['Committee1'], row['Committee2']]
                committees_filtered = [committee for committee in committees if committee]

                source = row['source']
                classification = row['Type']
                category = row['Category1']

                hearing_number_raw = row['Hearing #']

                # try to match by serial number
                if hearing_number_raw:
                    try:
                        hearing_number = re.search(r'\d{2,}-\d{1,}', hearing_number_raw).group(0)
                        matched_events = Event.objects.filter(extras__hearing_number__endswith=hearing_number)

                        for event in matched_events:
                            self.new_category(event, category, row_count)
                            self.match_count += 1

                        matched = True

                    except AttributeError:
                        self.bad_rows.append("Row " + str(row_count) + ": Unrecognized hearing number " + hearing_number_raw + " on " + name)

                # try to match by date and committees

                if not matched:
                # find the start_date and participants
                    committee_qs = Committee.objects.filter(lugar_id__in=committees_filtered).values_list('organization', flat=True)
                    committee_set = set(committee for committee in committee_qs)
                    matched_events = Event.objects.filter(participants__ino=committee_set).extra({'opencivicdata_eventparticipant.id': "CAST(opencivicdata_eventparticipant.id as TEXT)"})

                    EventParticipant.objects.filter(organization__in=committee_set, event__start_date=start_date)
                    print(matched_events)

                # matching_hearings = Event.participants.filter(entity_type='organization', start_date=start_date, participants=participants)
                # print(matching_hearings)

                # find matching_hearings on the same day and with the same event participants
                # matching_hearings = Event.objects.filter(start_date=start_date, participants=participants)
                # print(matching_hearings)

                # if matching_hearings == 0 and name:
                #     create new hearing
                #
                # if matching_hearings == 1:
                #     assign category to existing hearing
                #
                # if matching_hearings > 1:
                #
                #     no_match = True
                #
                #     for hearing in matching_hearings:
                #         if hearing name matches name:
                #             assign category to that hearing
                #             no_match = False
                #
                #     if no_match:
                #         log to bad_rows

                # if name:
                #     # get or create hearing
                #     event, created = Event.objects.get_or_create(jurisdiction_id = self.jurisdiction_id,
                #                     name = name,
                #                     start_date = start_date,
                #                     classification = classification)
                #
                #     # save committee data
                #     for committee in committees:
                #         if committee:
                #             self.new_event_participant(committee, event, row_count)
                #
                #     if created:
                #         # save event source
                #         source = EventSource.objects.create(event=event, note="spreadsheet", url=source)
                #
                #         # save category data
                #         try:
                #             hearing_category = HearingCategory.objects.create(event=event, category_id=category)
                #         except IntegrityError:
                #             self.bad_rows.append("Row " + str(row_count) + ": Unrecognized category " + category + " on " + event.name)
                #
                #     row_count += 1

    def get_committee(self, committee_name, parent, committee_key):
        classification = "committee"
        organization_exact = Organization.objects.filter(name=committee_name, parent=parent, classification=classification)
        organization_contains = Organization.objects.filter(name__icontains=committee_name, parent=parent, classification=classification)

        if organization_exact.count() == 1:
            return organization_exact[0]
        else:
            if organization_contains.count() == 1:
                return organization_contains[0]
            elif organization_contains.count() == 0:
                organization_other_name = Organization.objects.filter(other_names__name__icontains=committee_name, parent=parent, classification=classification)
                try:
                    return organization_other_name[0]
                except IndexError:
                    new_committee, _ = Committee.objects.get_or_create(lugar_id=committee_key, lugar_name=committee_name)
                    self.bad_rows.append("Not recognized: " + committee_key + ", " + committee_name)
            else:
                self.bad_rows.append("Multiple possible committees for " + committee_key + ": " + committee_name)

    def new_event_participant(self, committee_key, event, row_count):
        try:
            name = Committee.objects.get(lugar_id=committee_key).organization.name
            organization = Committee.objects.get(lugar_id=committee_key).organization
            entity_type = "organization"
            committee, created = EventParticipant.objects.get_or_create(name=name, event=event, organization=organization, entity_type=entity_type)

        except (ObjectDoesNotExist, AttributeError, ValueError) as e:
            self.bad_rows.append("Row " + str(row_count) + ": Bad committee key " + committee_key)

    def new_category(self, event, category, row_count):
        try:
            hearing_category = HearingCategory.objects.create(event=event, category_id=category)

        except IntegrityError:
            self.bad_rows.append("Row " + str(row_count) + ": Unrecognized category " + category + " on " + event.name)

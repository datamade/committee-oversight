import os
import csv
import re

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
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
        self.noop_count = 0
        self.updated_count = 0
        self.created_count = 0

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
        self.bad_rows.append("\nHouse Hearings\n")
        self.add_house_hearings()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': House hearings imported successfully!'))

        self.stdout.write(str(datetime.now()) + ': Creating database entries for the Senate...')
        self.bad_rows.append("\nSenate Hearings\n")
        self.add_senate_hearings()
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Senate hearings imported successfully!'))

        # Write bad category rows to file
        with open('bad_rows.txt', 'a') as f:
            for row in self.bad_rows:
                f.write(row + '\n')

        # Log match and created counts
        self.stdout.write("Hearings already in database: " + str(self.noop_count))
        self.stdout.write("Hearings updated: " + str(self.updated_count))
        self.stdout.write("Hearings created: " + str(self.created_count))

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
                        committee, _ = Committee.objects.get_or_create(lugar_id=committee_key,
                                                                           lugar_name=committee_name,
                                                                           organization=organization)

    def add_senate_committees(self):
        senate = Organization.objects.get(name="United States Senate")

        with open('data/final/senate_committees_edited.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['Committees']
                committee_name = row['b']
                classification = "committee"

                organization = self.get_committee(committee_name, senate, committee_key)
                committee, _ = Committee.objects.get_or_create(lugar_id=committee_key,
                                                                   lugar_name=committee_name,
                                                                   organization=organization)

    def add_house_hearings(self):
        with open('data/final/house.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            self.row_count = 2

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
                    print("\nHouse row " + str(self.row_count) + ": " + name)
                    exists = self.does_hearing_exist(name, start_date, classification, category)

                    if exists:
                        print("Already exists!")
                        self.noop_count += 1

                    else:
                        participating_committees = self.get_participating_committees(committee1, committee2, subcommittee1, subcommittee2)
                        event = self.match_by_date_and_participants(name, participating_committees, start_date, category, source, classification)

                        if event:
                            self.update_hearing(event, category, source)
                        else:
                            self.create_hearing(name, start_date, participating_committees, classification, category, source)

                self.row_count += 1

    def add_senate_hearings(self):
        with open('data/final/senate.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            self.row_count = 2

            for row in reader:
                name = row['Hearing/Report']
                start_date = row['Date'].split('T', 1)[0]
                source = row['source']
                classification = row['Type']
                category = row['Category1']
                hearing_number_raw = row['Hearing #']

                committees = [row['Committee1'], row['Committee2']]
                participating_committees = [committee for committee in committees if committee]

                if name:
                    print("\nSenate row " + str(self.row_count) + ": " + name)
                    exists = self.does_hearing_exist(name, start_date, classification, category)

                    if exists:
                        print("Already exists!")
                        self.noop_count += 1

                    else:
                        events = self.match_by_hearing_number(hearing_number_raw, name, category, source)
                        if events is not None:
                            # hearing numbers can be non-unique if a hearing has multiple sessions
                            # these are recorded in the Lugar data as separate events
                            for event in events:
                                self.update_hearing(event, category, source)
                                break

                        event = self.match_by_date_and_participants(name, participating_committees, start_date, category, source, classification)

                        if event:
                            self.update_hearing(event, category, source)
                        else:
                            self.create_hearing(name, start_date, participating_committees, classification, category, source)

                self.row_count += 1

    def get_committee(self, committee_name, parent, committee_key):
        classification = "committee"
        organization_exact = Organization.objects.filter(name=committee_name, parent=parent, classification=classification)

        if organization_exact.count() == 1:
            return organization_exact[0]

        organization_contains = Organization.objects.filter(name__icontains=committee_name, parent=parent, classification=classification)
        if organization_contains.count() == 1:
            return organization_contains[0]
        elif organization_contains.count() == 0:
            organization_other_name = Organization.objects.filter(other_names__name__icontains=committee_name, parent=parent, classification=classification)
            try:
                return organization_other_name[0]
            except IndexError:
                committee, _ = Committee.objects.get_or_create(lugar_id=committee_key, lugar_name=committee_name)
                self.bad_rows.append("Not recognized: " + committee_key + ", " + committee_name)
        else:
            self.bad_rows.append("Multiple possible committees for " + committee_key + ": " + committee_name)

    def get_participating_committees(self, committee1, committee2, subcommittee1, subcommittee2):
        # get committees into a edited list format
        # committee codes with a zero appended indicate "full committee"
        # and only the full committee will be recorded as an event participant
        # hearings with a subcommittee listed will only have the subcommittee saved,
        # as the full committee is attached as a parent
        participating_committees = []

        if (committee1 and not subcommittee1) or (subcommittee1 == (committee1 + str(0))):
            participating_committees.append(committee1)
        elif committee1:
            participating_committees.append(subcommittee1)

        if (committee2 and not subcommittee2) or (subcommittee2 == (committee2 + str(0))):
            participating_committees.append(committee2)
        elif committee2:
            participating_committees.append(subcommittee2)

        return participating_committees

    def new_event_participant(self, committee_key, event):
        try:
            organization = Committee.objects.get(lugar_id=committee_key).organization
            entity_type = "organization"
            committee, created = EventParticipant.objects.get_or_create(name=organization.name, event=event, organization=organization, entity_type=entity_type)

        except (ObjectDoesNotExist, AttributeError, ValueError) as e:
            self.bad_rows.append("Row " + str(self.row_count) + ": Bad committee key " + committee_key)

    def new_category(self, event, category):
        try:
            hearing_category, created = HearingCategory.objects.get_or_create(event=event, category_id=category)
            return created

        # in case manually entered hearings have a mistakenly category not described in this fixture:
        # https://github.com/datamade/committee-oversight/blob/master/committeeoversightapp/fixtures/hearingcategorytype.json
        except IntegrityError:
            self.bad_rows.append("Row " + str(self.row_count) + ": Unrecognized category " + category + " on " + event.name)
            return False

    def new_source(self, event, note, url):
        source, created = EventSource.objects.get_or_create(event=event, note=note, url=url)
        return created

    def does_hearing_exist(self, name, start_date, classification, category):
        try:
            event = Event.objects.get(
                                name=name,
                                start_date=start_date,
                                jurisdiction_id=self.jurisdiction_id,
                                classification=classification,
                                sources__note="spreadsheet",
                                hearingcategory__category_id=category
                                )
            return True
        except ObjectDoesNotExist:
            return False
        except MultipleObjectsReturned:
            self.bad_rows.append("Row " + str(self.row_count) + ": Multiple matching committees found for " + name + " on " + start_date)
            return True

    def match_by_hearing_number(self, hearing_number_raw, name, category, source):
        if hearing_number_raw:
            try:
                hearing_number = re.search(r'\d{2,}-\d{1,}', hearing_number_raw).group(0)
                events = Event.objects.filter(extras__hearing_number__endswith=hearing_number)
                return events

            except AttributeError:
                self.bad_rows.append("Row " + str(self.row_count) + ": Unrecognized hearing number " + hearing_number_raw + " on " + name)
                return
        else:
            return

    def match_by_date_and_participants(self, name, participating_committees, start_date, category, source, classification):
        try:
            committee_qs = Committee.objects.filter(lugar_id__in=participating_committees)
            committee_set = set(committee.organization.name for committee in committee_qs)
            matched_events = Event.objects.filter(participants__name__in=committee_set, start_date=start_date).distinct()
        except ValueError:
            matched_events = []
            self.bad_rows.append("Row " + str(self.row_count) + ": Bad committee value in " + str(participating_committees))

        if len(matched_events) == 1:
            return matched_events[0]

        elif len(matched_events) > 1:
            for event in matched_events:
                if event.name.lower() == name.lower():
                    return event
                else:
                    self.bad_rows.append("Row " + str(self.row_count) + ": Multiple possible matches but no matching name " + str(matched_events))
                    return
        else:
            return

    def update_hearing(self, event, category, source):
        category_created = self.new_category(event, category)
        source_created = self.new_source(event, "spreadsheet", source)

        if category_created or source_created:
            self.updated_count += 1
            print("Match #" + str(self.updated_count) + ": " + event.name)
        else:
            self.noop_count += 1
            print("Already exists!")

    def create_hearing(self, name, start_date, participating_committees, classification, category, source):
        event = Event.objects.create(name=name,
                                     start_date=start_date,
                                     jurisdiction_id=self.jurisdiction_id,
                                     classification=classification)

        for committee in participating_committees:
            self.new_event_participant(committee, event)

        self.new_category(event, category)
        self.new_source(event, "spreadsheet", source)
        self.created_count += 1
        print("Created #" + str(self.created_count) + ": " + event.name)

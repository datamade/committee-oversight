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

ScrapedEvents = Event.objects.exclude(sources__note='spreadsheet')

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

            # we are doing this instead of enumerate so that
            # so that we can get a handle on the row in error messages
            # in some methods that will be down the stack
            self.row_count = 2
            non_blank_rows = 1

            for row in reader:

                source = csvfile.name
                start_date = row['Date'].split('T', 1)[0]
                name = row['Hearing/Report']
                classification = row['Type']
                category = row['Category1']

                committee1 = row['Committee1']
                committee2 = row['Committee2']
                subcommittee1 = row['Subcommittee']
                subcommittee2 = row['Subcommittee2']

                participating_committees = self.get_participating_committees(committee1,
                                                                             committee2,
                                                                             subcommittee1,
                                                                             subcommittee2)


                if name:
                    non_blank_rows += 1

                    self.stdout.write("\nHouse row " + str(self.row_count) + ": " + name)
                    exists = self.does_hearing_exist(name,
                                                     start_date,
                                                     participating_committees,
                                                     classification,
                                                     category)

                    if exists:
                        self.stdout.write("Already exists!")
                        self.noop_count += 1

                    else:
                        event = self.match_by_date_and_participants(name,
                                                                    participating_committees,
                                                                    start_date)

                        if event:
                            self.update_hearing(event,
                                                name,
                                                start_date,
                                                participating_committees,
                                                classification,
                                                category,
                                                source)
                        else:
                            self.create_hearing(name,
                                                start_date,
                                                participating_committees,
                                                classification,
                                                category,
                                                source)

                self.row_count += 1

        lugar_in_db = len(Event.objects.filter(sources__url=csvfile.name))
        assert lugar_in_db == non_blank_rows


    def add_senate_hearings(self):
        with open('data/final/senate.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            # we are doing this instead of enumerate so that
            # so that we can get a handle on the row in error messages
            # in some methods that will be down the stack
            self.row_count = 2
            non_blank_rows = 1

            for row in reader:
                name = row['Hearing/Report']
                start_date = row['Date'].split('T', 1)[0]
                source = csvfile.name
                classification = row['Type']
                category = row['Category1']
                hearing_number_raw = row['Hearing #']

                committees = [row['Committee1'], row['Committee2']]
                participating_committees = [committee for committee in committees if committee]
                participating_committees = Committee.objects.filter(lugar_id__in=participating_committees, organization__isnull=False)

                if name:
                    non_blank_rows += 1

                    self.stdout.write("\nSenate row " + str(self.row_count) + ": " + name)
                    exists = self.does_hearing_exist(name,
                                                     start_date,
                                                     participating_committees,
                                                     classification,
                                                     category)

                    if exists:
                        self.stdout.write("Already exists!")
                        self.noop_count += 1

                    else:
                        events = self.match_by_hearing_number(hearing_number_raw, name, category, source)
                        if events is not None:
                            # hearing numbers can be non-unique if a
                            # hearing has multiple sessions these are
                            # recorded in the Lugar data as separate
                            # events
                            for event in events:
                                self.update_hearing(event,
                                                    name,
                                                    start_date,
                                                    participating_committees,
                                                    classification,
                                                    category,
                                                    source)

                        else:
                            event = self.match_by_date_and_participants(name,
                                                                        participating_committees,
                                                                        start_date)

                            if event:
                                self.update_hearing(event,
                                                    name,
                                                    start_date,
                                                    participating_committees,
                                                    classification,
                                                    category,
                                                    source)
                            else:
                                self.create_hearing(name,
                                                    start_date,
                                                    participating_committees,
                                                    classification,
                                                    category,
                                                    source)

                self.row_count += 1

        lugar_in_db = len(Event.objects.filter(sources__url=csvfile.name))
        assert lugar_in_db == non_blank_rows


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

        participating_committees = [committee for committee in participating_committees if committee.isdigit()]

        committee_qs = Committee.objects.filter(lugar_id__in=participating_committees, organization__isnull=False)

        return committee_qs

    def new_event_participant(self, committee, event):
        try:
            entity_type = "organization"
            new_committee, created = EventParticipant.objects.get_or_create(name=committee.name, event=event, organization=committee, entity_type=entity_type)

        except (ObjectDoesNotExist, AttributeError, ValueError) as e:
            self.bad_rows.append("Row " + str(self.row_count) + ": Bad committee key " + committee)
        except MultipleObjectsReturned:
            pass

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

    def does_hearing_exist(self, name, start_date, participating_committees, classification, category):
        try:
            if len(participating_committees):
                Event.objects.filter(participants__organization__in=participating_committees.values('organization'))\
                             .exclude(~Q(participants__organization__in=participating_committees.values('organization')))\
                             .distinct()\
                             .get(name=name,
                                  start_date=start_date,
                                  jurisdiction_id=self.jurisdiction_id,
                                  classification=classification,
                                  sources__note="spreadsheet",
                                  hearingcategory__category_id=category
                )
            else:
                Event.objects.get(name=name,
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
                events = ScrapedEvents.filter(extras__hearing_number__endswith=hearing_number)
                if len(events) > 0:
                    return events
                else:
                    return

            except AttributeError:
                self.bad_rows.append("Row " + str(self.row_count) + ": Unrecognized hearing number " + hearing_number_raw + " on " + name)
                return
        else:
            return

    def match_by_date_and_participants(self, name, participating_committees, start_date):
        try:
            matched_events = ScrapedEvents.filter(participants__organization__in=participating_committees.values('organization'), start_date=start_date).distinct()
        except ValueError:
            matched_events = []
            print(participating_committees)
            self.bad_rows.append("Row " + str(self.row_count) + ": Bad committee value in " + str(participating_committees))

        if len(matched_events) == 1:
            return matched_events[0]

        elif len(matched_events) > 1:
            matched_events = matched_events.filter(name__iexact=name)
            if len(matched_events) == 1:
                return matched_events[0]
            else:
                self.bad_rows.append("Row " + str(self.row_count) + ": Multiple possible matches but no matching name " + str(matched_events))
                return
        else:
            return

    def update_hearing(self,
                       event,
                       name,
                       start_date,
                       participating_committees,
                       classification,
                       category,
                       source):

        event.name = name
        event.start_date = start_date
        event.classification = classification
        event.save()
        category_created = self.new_category(event, category)
        source_created = self.new_source(event, "spreadsheet", source)

        for committee in participating_committees:
            self.new_event_participant(committee.organization, event)

        if category_created or source_created:
            self.updated_count += 1
            self.stdout.write("Match #" + str(self.updated_count) + ": " + event.name)
        else:
            self.noop_count += 1
            self.stdout.write("Already exists!")

    def create_hearing(self, name, start_date, participating_committees, classification, category, source):
        event = Event.objects.create(name=name,
                                     start_date=start_date,
                                     jurisdiction_id=self.jurisdiction_id,
                                     classification=classification)

        for committee in participating_committees:
            self.new_event_participant(committee.organization, event)

        success = self.new_category(event, category)
        if success:
            self.new_source(event, "spreadsheet", source)
            self.created_count += 1
            self.stdout.write("Created #" + str(self.created_count) + ": " + event.name)
        else:
            event.delete()

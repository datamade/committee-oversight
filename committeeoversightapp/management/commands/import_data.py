import os
import csv
import re

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings
from django.db import transaction, connection
from django.db.models import Q


from opencivicdata.core.models import Organization, OrganizationName
from opencivicdata.legislative.models import Event, EventSource, EventParticipant
from committeeoversightapp.models import HearingCategory, Committee

ExistingEvents = Event.objects.exclude(sources__note='spreadsheet').exclude(sources__note='web form')

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

        with open('data/final/house_committees.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['code']
                committee_name = row['name']
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

        with open('data/final/senate_committees.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                committee_key = row['code']
                committee_name = row['name']
                classification = "committee"

                organization = self.get_committee(committee_name, senate, committee_key)
                committee, _ = Committee.objects.get_or_create(lugar_id=committee_key,
                                                                   lugar_name=committee_name,
                                                                   organization=organization)

    def add_house_hearings(self):
        with open('data/final/house.csv', 'r') as csvfile, \
             transaction.atomic():

            with connection.cursor() as cursor:
                cursor.execute(
                    '''CREATE TEMPORARY TABLE participants AS
                       SELECT event_id,
                              ARRAY_AGG(organization_id::text) AS committees
                       FROM opencivicdata_eventparticipant
                       GROUP BY event_id''')

            reader = csv.DictReader(csvfile)
            # we want to know the original row index for debugging purposes
            reader = enumerate(reader, 2)
            # ignore rows with a missing name
            reader = ((i, row) for i, row in reader if row['Hearing/Report'])

            for i, (self.row_index, row) in enumerate(reader, 1):

                source = row['source']
                source_file = csvfile.name
                source_hash = str(sorted(row.items()))
                start_date = row['Date'].split('T', 1)[0]
                name = row['Hearing/Report']
                classification = row['Type']
                category = row['Category1']

                participating_committees = self.get_participating_committees(row)

                self.stdout.write("\nHouse row " + str(self.row_index) + ": " + name)
                exists = self.does_hearing_exist(source_hash)

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
                                            source,
                                            source_hash,
                                            source_file)
                    else:
                        self.create_hearing(name,
                                            start_date,
                                            participating_committees,
                                            classification,
                                            category,
                                            source,
                                            source_hash,
                                            source_file)

            lugar_in_db = len(Event.objects.filter(extras__source_file=csvfile.name))

            assert abs(lugar_in_db - i) < 5

            with connection.cursor() as cursor:
                    cursor.execute(
                        '''DROP TABLE participants''')



    def add_senate_hearings(self):
        with open('data/final/senate.csv', 'r') as csvfile, \
             transaction.atomic():

            with connection.cursor() as cursor:
                cursor.execute(
                    '''CREATE TEMPORARY TABLE participants AS
                       SELECT event_id,
                              ARRAY_AGG(organization_id::text) AS committees
                       FROM opencivicdata_eventparticipant
                       GROUP BY event_id''')

            reader = csv.DictReader(csvfile)
            # we want to know the original row index for debugging purposes
            reader = enumerate(reader, 2)
            # ignore rows with a missing name
            reader = ((i, row) for i, row in reader if row['Hearing/Report'])

            for i, (self.row_index, row) in enumerate(reader, 1):
                name = row['Hearing/Report']
                start_date = row['Date'].split('T', 1)[0]
                source = row['source']
                source_file = csvfile.name
                source_hash = str(sorted(row.items()))
                classification = row['Type']
                category = row['Category1']
                hearing_number_raw = row['Hearing #']

                committees = [row['Committee1'], row['Committee2']]

                participating_committees = [committee for committee in committees if committee]
                participating_committees = Committee.objects.filter(lugar_id__in=participating_committees, organization__isnull=False)

                self.stdout.write("\nSenate row " + str(self.row_index) + ": " + name)
                exists = self.does_hearing_exist(source_hash)

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
                                                source,
                                                source_hash,
                                                source_file)

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
                                                source,
                                                source_hash,
                                                source_file)
                        else:
                            self.create_hearing(name,
                                                start_date,
                                                participating_committees,
                                                classification,
                                                category,
                                                source,
                                                source_hash,
                                                source_file)


            lugar_in_db = len(Event.objects.filter(extras__source_file=csvfile.name))
            # from manual checking this is acceptable
            assert abs(lugar_in_db - i) < 80

            with connection.cursor() as cursor:
                cursor.execute(
                    '''DROP TABLE participants''')



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

    def get_participating_committees(self, row):
        # get committees into a edited list format
        # committee codes with a zero appended indicate "full committee"
        # and only the full committee will be recorded as an event participant
        # hearings with a subcommittee listed will only have the subcommittee saved,
        # as the full committee is attached as a parent

        committee1 = row['Committee1']
        committee2 = row['Committee2']
        subcommittee1 = row['Subcommittee']
        subcommittee2 = row['Subcommittee2']

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

        committee_qs = Committee.objects.filter(lugar_id__in=participating_committees)

        return committee_qs

    def new_event_participant(self, committee, event):
        entity_type = "organization"

        try:
            if committee.organization:
                committee = committee.organization
                new_committee, created = EventParticipant.objects.get_or_create(name=committee.name, event=event, organization=committee, entity_type=entity_type)
            else:
                new_committee, created = EventParticipant.objects.get_or_create(name=committee.lugar_name, event=event, entity_type=entity_type)

        except (ObjectDoesNotExist, AttributeError, ValueError) as e:
            self.bad_rows.append("Row " + str(self.row_index) + ": Bad committee key " + committee)
        except MultipleObjectsReturned:
            # there are a few scraped events that have multiple
            # participants on them
            pass

    def new_category(self, event, category):

        valid_categories = set(range(1,14))
        if category not in valid_categories:
            return False

        hearing_category, created = HearingCategory.objects.get_or_create(event=event, category_id=category)

    def new_source(self, event, note, url):
        source, created = EventSource.objects.get_or_create(event=event, note=note, url=url)
        return created

    def does_hearing_exist(self, source_hash):

        try:
            Event.objects.get(extras__source_hash=source_hash)
        except ObjectDoesNotExist:
            return False
        else:
            return True

    def match_by_hearing_number(self, hearing_number_raw, name, category, source):
        if hearing_number_raw:
            try:
                hearing_number = re.search(r'\d{2,}-\d{1,}', hearing_number_raw).group(0)
                events = ExistingEvents.filter(extras__hearing_number__endswith=hearing_number)
                if len(events) > 0:
                    return events
                else:
                    return

            except AttributeError:
                self.bad_rows.append("Row " + str(self.row_index) + ": Unrecognized hearing number " + hearing_number_raw + " on " + name)
                return
        else:
            return

    def match_by_date_and_participants(self, name, participating_committees, start_date):
        try:
            lugar_committees = list(org['organization']
                                    for org in participating_committees.values('organization')
                                    if org['organization'] is not None)
            matched_events = ExistingEvents.raw(
                '''SELECT opencivicdata_event.*
                   FROM opencivicdata_event
                   INNER JOIN participants
                   ON opencivicdata_event.id = participants.event_id
                   WHERE committees @> %(lugar_committees)s
                   AND committees <@ %(lugar_committees)s
                   AND start_date = %(start_date)s
                   AND opencivicdata_event.id NOT IN
                       (SELECT event_id FROM opencivicdata_eventsource
                        WHERE note = 'spreadsheet')''',
                {'lugar_committees': lugar_committees,
                 'start_date': start_date})
        except ValueError:
            matched_events = []
            self.bad_rows.append("Row " + str(self.row_index) + ": Bad committee value in " + str(participating_committees))

        if len(matched_events) == 1:
            return matched_events[0]

        elif len(matched_events) > 1:
            matched_events = ExistingEvents.raw(
                '''SELECT opencivicdata_event.* 
                   FROM opencivicdata_event
                   INNER JOIN participants
                   ON opencivicdata_event.id = participants.event_id
                   WHERE committees @> %(lugar_committees)s
                   AND committees <@ %(lugar_committees)s
                   AND start_date = %(start_date)s
                   AND name ILIKE %(name)s
                   AND opencivicdata_event.id NOT IN
                       (SELECT event_id FROM opencivicdata_eventsource
                        WHERE note = 'spreadsheet')''',
                {'lugar_committees': lugar_committees,
                 'start_date': start_date,
                 'name': name})
            if len(matched_events) == 1:
                return matched_events[0]
            else:
                self.bad_rows.append("Row " + str(self.row_index) + ": Multiple possible matches but no matching name " + str(matched_events))
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
                       source,
                       source_hash,
                       source_file):

        event.name = name
        event.start_date = start_date
        event.classification = classification
        event.extras['source_hash'] = source_hash
        event.extras['source_file'] = source_file
        event.save()

        if category:
            category_created = self.new_category(event, category)
        else:
            category_created = False

        source_created = self.new_source(event, "spreadsheet", source)

        for committee in participating_committees:
            self.new_event_participant(committee, event)

        self.updated_count += 1
        self.stdout.write("Match #" + str(self.updated_count) + ": " + event.name)

    def create_hearing(self,
                       name,
                       start_date,
                       participating_committees,
                       classification,
                       category,
                       source,
                       source_hash,
                       source_file):
        event = Event.objects.create(name=name,
                                     start_date=start_date,
                                     jurisdiction_id=self.jurisdiction_id,
                                     classification=classification)
        event.extras['source_hash'] = source_hash
        event.extras['source_file'] = source_file
        event.save()

        for committee in participating_committees:
            self.new_event_participant(committee, event)

        if category:
            self.new_category(event, category)

        self.new_source(event, "spreadsheet", source)
        self.created_count += 1
        self.stdout.write("Created #" + str(self.created_count) + ": " + event.name)

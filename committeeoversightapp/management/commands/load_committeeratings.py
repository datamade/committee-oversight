from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import datetime

from committeeoversightapp.models import Congress, CommitteeOrganization, \
                                         CommitteeRating, Event


class Command(BaseCommand):
    def handle(self, **options):
        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Starting committee rating update'))

        for congress in Congress.objects.all():
            for committee in CommitteeOrganization.objects.permanent_committees():
                self.build_committee_rating(congress, committee)

        self.stdout.write(self.style.SUCCESS(str(datetime.now()) + ': Committee rating update completed!'))

    def build_committee_rating(self, congress, committee):
        committee_hearings = committee.hearings.filter(
            start_date__range=(
                congress.start_date,
                congress.end_date
            )
        )

        # Investigative Oversight = Agency Conduct Hearings + Private Sector Hearings
        investigative_oversight_hearings=self.count_by_category(
            committee_hearings,
            ['Agency Conduct', 'Private Sector Oversight']
        )

        # Policy/Legislative = Policy Hearings + Legislative Hearings + Closed Hearings
        policy_legislative_hearings=self.count_by_category(
            committee_hearings,
            ['Legislative', 'Policy', 'Closed']
        )

        # Total = Agency Conduct + Private Sector + Policy + Legislative
        # + Nominations + Fact Finding + Field + Closed
        total_hearings=self.count_by_category(
            committee_hearings,
            ['Nominations', 'Legislative', 'Policy', 'Agency Conduct',
             'Private Sector Oversight', 'Fact Finding', 'Field', 'Closed']
        )

        # This ratings methodology was designed by the Lugar Center
        chp_points = (7 * investigative_oversight_hearings) + \
            (2 * policy_legislative_hearings) + \
            (total_hearings)

        rating, _ = CommitteeRating.objects.get_or_create(
            congress=congress,
            committee=committee
        )

        rating.investigative_oversight_hearings = \
            investigative_oversight_hearings
        rating.policy_legislative_hearings = policy_legislative_hearings
        rating.total_hearings = total_hearings
        rating.chp_points = chp_points
        rating.save()

        self.stdout.write(
            'Added rating counts for {} to {}. Total points = {}.'.format(
                congress.label,
                committee.name,
                chp_points
            )
        )

    def count_by_category(self, committee_hearings, category_list):
        return committee_hearings.filter(
            hearingcategory__category__name__in=category_list
        ).count()

from itertools import chain
from random import randint

from django.core.management.base import BaseCommand

from opencivicdata.core.models import Organization

from committeeoversightapp.models import CommitteeRating


class Command(BaseCommand):
    RATINGS_FIXTURE = {
        'Senate Committee on Veterans\' Affairs': {
            115: 'D',
            114: 'A',
            113: 'C',
            112: 'C-',
            111: 'A',
            110: 'C',
            109: 'B',
            108: 'F',
            107: 'F',
        },
        'Senate Committee on Energy and Natural Resources': {
            115: 'F',
            114: 'C',
            113: 'B+',
            112: 'D-',
            111: 'A',
            110: 'D',
            109: 'B',
            108: 'C',
            107: 'F',
        },
    }

    @property
    def possible_ratings(self):
        if not getattr(self, '_possible_ratings', None):
            ratings_tuples = (('{}+'.format(letter), letter, '{}-'.format(letter)) for letter in 'ABCDF')

            # (('A+', 'A', 'A-'), ..., ('F+', 'F', 'F-')) => ['A+', ..., 'F-']
            self._possible_ratings = list(chain.from_iterable(ratings_tuples))

        return self._possible_ratings

    def handle(self, **options):
        '''
        N.b., if we need to handle a large number of ratings in the future,
        consider batching bulk_creates, as modeled in the docs:
        https://docs.djangoproject.com/en/2.2/ref/models/querysets/#bulk-create

        I wrote this envisioning we'd receive ratings in a flat CSV file (or
        in a file we could convert to a flat CSV) containing columns for
        committee name (or some other unique identifier, e.g., Lugar ID),
        congress number, and rating.

        We could easily revise this to accept such input by iterating over a
        CSV reader grouped by the committee identifier, rather than the
        fixture dictionary.
        '''
        committee_ratings = []

        for committee, ratings in self.RATINGS_FIXTURE.items():
            committee_ratings += list(self.build_commitee_ratings(committee, ratings))

        outstanding_committees = Organization.objects.all()\
                                                     .filter(classification='committee',
                                                             parent_id__name__in=['United States House of Representatives', 'United States Senate'])\
                                                     .exclude(name__in=list(self.RATINGS_FIXTURE.keys()))

        for committee in outstanding_committees:
            dummy_ratings = {c: self.random_rating() for c in self.congresses()}
            committee_ratings += list(self.build_commitee_ratings(committee, dummy_ratings))

        CommitteeRating.objects.bulk_create(committee_ratings)

    def build_commitee_ratings(self, committee, ratings):
        committee = Organization.objects.get(name=committee)

        for congress_id, rating in ratings.items():
            rating = CommitteeRating(committee=committee,
                                     congress=congress_id,
                                     rating=rating)

            self.stdout.write('Added {} rating for {} in {}'.format(rating.rating,
                                                                    committee.name,
                                                                    rating.congress_label))

            yield rating

    def congresses(self):
        '''
        Grab congresses from the (arbitrary) first committee in the ratings
        fixture.
        '''
        return self.RATINGS_FIXTURE[list(self.RATINGS_FIXTURE)[0]].keys()

    def random_rating(self):
        return self.possible_ratings[randint(0, len(self.possible_ratings) - 1)]

from django.core.management.base import BaseCommand

from opencivicdata.core.models import Organization

from committeeoversightapp.models import CommitteeRating


class Command(BaseCommand):
    RATINGS_FIXTURE = {
        'Senate Committee on Veterans\' Affairs': {
            116: 'B',
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
            116: 'C',
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

    def handle(self, **options):
        committee_ratings = []

        # N.b., if we need to handle a large number of ratings in the future,
        # consider batching bulk_creates, as modeled in the docs:
        # https://docs.djangoproject.com/en/2.2/ref/models/querysets/#bulk-create
        #
        # I wrote this envisioning we'd receive ratings in a flat CSV file (or
        # in a file we could convert to a flat CSV) containing columns for
        # committee name (or some other unique identifier, e.g., Lugar ID),
        # congress number, and rating.
        #
        # We could easily revise this to accept such input by iterating over a
        # CSV reader grouped by the committee identifier, rather than the
        # fixture dictionary.
        for committee, ratings in self.RATINGS_FIXTURE.items():
            committee = Organization.objects.get(name=committee)

            for congress_id, rating in ratings.items():
                rating = CommitteeRating(committee=committee,
                                         congress=congress_id,
                                         rating=rating)

                committee_ratings.append(rating)

                self.stdout.write('Added {} rating for {} in {}'.format(rating.rating,
                                                                        committee.name,
                                                                        rating.congress_label))

        CommitteeRating.objects.bulk_create(committee_ratings)

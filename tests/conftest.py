import pytest
from committeeoversight.wsgi import *

from committeeoversightapp.models import HearingCategory
from opencivicdata.legislative.models import Event
from opencivicdata.core.models import Jurisdiction, Division


@pytest.fixture
@pytest.mark.django_db
def division():
    division = Division.objects.create(
        name='United States',
        id='ocd-division/country:us'
        )

    return division


@pytest.fixture
@pytest.mark.django_db
def jurisdiction(division):
    jurisdiction = Jurisdiction.objects.create(
        name='United States of America',
        division=division
        )

    return jurisdiction

@pytest.fixture
@pytest.mark.django_db
def hearing(jurisdiction):
    hearing = Event.objects.create(
        jurisdiction=jurisdiction,
        name='Test Hearing'
        )

    return hearing

import pytest

@pytest.mark.django_db
def test_hearing(hearing):
    assert hearing.jurisdiction.name == 'United States of America'
    assert hearing.name == 'Test Hearing'

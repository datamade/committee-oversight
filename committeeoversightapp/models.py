from django.db import models
from opencivicdata.core.models import Organization
from opencivicdata.legislative.models import Event, EventParticipant, EventDocument

class HearingCategoryType(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100, primary_key=False)

    def __str__(self):
        return u'({0}) {1}'.format(self.id, self.name)

class HearingCategory(models.Model):
    event = models.ForeignKey(Event, null=True, on_delete=models.CASCADE)
    category = models.ForeignKey(HearingCategoryType, null=True, on_delete=models.CASCADE)

class WitnessDetails(models.Model):
    witness = models.ForeignKey(EventParticipant, on_delete=models.CASCADE)
    document = models.ForeignKey(EventDocument, null=True, blank=True, on_delete=models.CASCADE)
    organization = models.CharField(max_length=100, null=True, blank=True, primary_key=False)
    retired = models.BooleanField(default=False)

class Committee(models.Model):
    lugar_id = models.IntegerField(null=True, blank=True, primary_key=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

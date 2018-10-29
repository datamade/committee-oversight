from django.db import models
from opencivicdata.legislative.models import Event, EventParticipant, EventDocument

class HearingCategoryType(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100, primary_key=False)

    def __str__(self):
        return u'({0}) {1}'.format(self.id, self.name)

class HearingCategory(models.Model):
    event = models.ForeignKey(Event, null=True, on_delete=models.CASCADE)
    category = models.ForeignKey(HearingCategoryType, null=True, on_delete=models.CASCADE)

class WitnessDocument(models.Model):
    witness = models.ForeignKey(EventParticipant, on_delete=models.CASCADE)
    document = models.ForeignKey(EventDocument, on_delete=models.CASCADE)

# witness org as extra in eventparticipant
# model linking witnesses and documents

from django.forms import ModelForm, TextInput, HiddenInput, SelectMultiple, \
                         ModelChoiceField, formset_factory
from opencivicdata.legislative.models import Event, EventParticipant
from opencivicdata.core.models import Jurisdiction, Organization

# add hearing events
class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = ['jurisdiction', 'name', 'start_date', 'classification', 'status']
        labels = {
            'name': ('Hearing Title'),
            'start_date': ('Date'),
            'classification': ('Type')
        }
        widgets = {
            'jurisdiction': HiddenInput()
            }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        jurisdiction = Jurisdiction.objects.get(name='United States of America')
        self.fields['jurisdiction'].initial = jurisdiction
        self.fields['status'].initial = "confirmed"


# add committees as event participants
class CommitteeForm(ModelForm):
    class Meta:
        model = EventParticipant
        fields = ['name', 'entity_type']
        widgets = {
            'entity_type': HiddenInput()
            }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.fields['entity_type'].initial = "organization"

    name = ModelChoiceField(label='Committee or subcommittee', queryset=Organization.objects.filter(classification='committee'))

CommitteeFormset = formset_factory(CommitteeForm, extra=1)

# add committee members as event participants
class CommitteeMemberForm(ModelForm):
    class Meta:
        model = EventParticipant
        fields = ['name', 'entity_type']
        widgets = {
            'entity_type': HiddenInput()
            }
        labels = {
            'name': ('Committee member present')
        }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.fields['entity_type'].initial = "committee member"

CommitteeMemberFormset = formset_factory(CommitteeMemberForm, extra=1)

# add witnesses as event participants
class WitnessForm(ModelForm):
    class Meta:
        model = EventParticipant
        fields = ['name', 'entity_type']
        widgets = {
            'entity_type': HiddenInput()
            }
        labels = {
            'name': ('Witness')
        }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.fields['entity_type'].initial = "person"

WitnessFormset = formset_factory(WitnessForm, extra=1)

# next: figure out how to render multiple forms in Django view, maybe turn these into formsets, get documentlink squared away

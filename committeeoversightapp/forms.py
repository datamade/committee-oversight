from django.forms import ModelForm, TextInput, HiddenInput, SelectMultiple, \
                         ModelMultipleChoiceField, formset_factory, Form
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
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        # self.fields['name'].widget.attrs['class'] = 'basic-multiple'
        # self.fields['name'].widget.attrs['multiple'] = 'multiple'

    name = ModelMultipleChoiceField(label='Committees/subcommittees', queryset=Organization.objects.filter(classification='committee'))

# add committee members as event participants
class CommitteeMemberForm(ModelForm):
    class Meta:
        model = EventParticipant
        fields = ['name']

    name = ModelMultipleChoiceField(label='Committee members present', queryset=Organization.objects.filter(classification='committee member'))

# add witnesses as event participants
class WitnessForm(ModelForm):
    class Meta:
        model = EventParticipant
        fields = ['name']

    name = ModelMultipleChoiceField(label='Witnesses', queryset=Organization.objects.filter(classification='person'))

# next: figure out how to render multiple forms in Django view, maybe turn these into formsets, get documentlink squared away

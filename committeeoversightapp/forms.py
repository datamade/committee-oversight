from django.forms import ModelForm, Form, TextInput, HiddenInput, DateField, DateInput, \
                         ModelMultipleChoiceField, ChoiceField, CharField, Textarea
from opencivicdata.legislative.models import Event, EventParticipant
from opencivicdata.core.models import Jurisdiction, Organization
from .customfields import GroupedModelMultiChoiceField

# add hearing events
class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = ['jurisdiction', 'name', 'start_date', 'classification', 'status']
        labels = {
            'name': ('Hearing Title'),
            'start_date': ('Date')
        }
        widgets = {
            'jurisdiction': HiddenInput()
            }

    start_date = DateField(
        widget=DateInput(attrs={'placeholder': 'yyyy-mm-dd'})
    )

    CHOICES = (('', '-----------'),
               ("Appropriations", "Appropriations"),
               ("Authorization Hearing", "Authorization Hearing"),
               ("Field Hearing", "Field Hearing"),
               ("Hearing", "Hearing"),
               ("Oversight Hearing", "Oversight Hearing"),
               ("Nomination Hearing", "Nomination Hearing")
              )
    classification = ChoiceField(
        label='Hearing type',
        choices=CHOICES
        )

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
        self.fields['name'].widget.attrs['class'] = 'basic-multiple'
        self.fields['name'].widget.attrs['multiple'] = 'multiple'

    name = GroupedModelMultiChoiceField(
        label='Committees/subcommittees',
        queryset=Organization.objects.filter(classification='committee').order_by('parent__name'),
        group_by_field='parent'
        )

# add committee members as event participants
class CommitteeMemberForm(Form):
    name = CharField(label='Committee members present (comma separated list)',
        widget=Textarea(attrs={'rows':4, 'cols':15}),
        required=False
    )

# add witnesses as event participants
class WitnessForm(Form):
    name = CharField(
        label='Witnesses (comma separated list)',
        widget=Textarea(attrs={'rows':4, 'cols':15}),
        required=False
    )

# add a field for transcript url
class TranscriptForm(Form):
    url = CharField(
        label='Transcript URL',
        required=False
    )

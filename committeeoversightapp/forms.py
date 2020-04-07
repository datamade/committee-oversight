from django.forms import ModelForm, Form, TextInput, HiddenInput, DateField, DateInput, \
                         ModelChoiceField, ModelMultipleChoiceField, ChoiceField, \
                         CharField, BooleanField, formset_factory
from opencivicdata.legislative.models import Event, EventParticipant
from opencivicdata.core.models import Jurisdiction, Organization

from .models import HearingCategoryType, WitnessDetails, CommitteeOrganization
from .customfields import GroupedModelMultiChoiceField


# add hearing events
class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = ['jurisdiction', 'name', 'start_date', 'classification']
        labels = {
            'name': ('Hearing Title'),
        }
        widgets = {
            'jurisdiction': HiddenInput(),
            'classification': HiddenInput()
            }

    start_date = DateField(
        widget=DateInput(attrs={'type':'date'}),
        label='Date'
    )

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        try:
            jurisdiction = Jurisdiction.objects.get(name='United States of America')
            self.fields['jurisdiction'].initial = jurisdiction
        except:
            pass

        self.fields['classification'].initial = "Hearing"

# add committees as event participants
class CommitteeForm(ModelForm):
    class Meta:
        model = EventParticipant
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['class'] = 'basic-multiple'
        self.fields['name'].widget.attrs['multiple'] = 'multiple'

    name = GroupedModelMultiChoiceField(
        label='Committees/subcommittees',
        queryset=CommitteeOrganization.objects.filter(classification='committee').order_by('parent__name'),
        group_by_field='parent',
        )

class CommitteeEditForm(CommitteeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False

# add a field for transcript url
class TranscriptForm(Form):
    transcript_url = CharField(
        label='Transcript URL',
        required=False
    )
    opening_statement_chair = CharField(
        label='Chair Opening Statement URL',
        required=False
    )
    opening_statement_rm = CharField(
        label='Ranking Member Opening Statement URL',
        required=False
    )

# add category as foreign key in table HearingCategory
class CategoryForm(Form):
    category = ModelChoiceField(
        queryset=HearingCategoryType.objects.all(),
        required=False
    )

# when editing a hearing, category is not required
class CategoryEditForm(CategoryForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False

# add witnesses as event participants
class WitnessForm(Form):
    name = CharField(
        label='Witness name'
    )

    organization = CharField(
        label='Witness organization',
        required=False
    )

    url = CharField(
        label='Witness statement URL',
        required=False
    )

    retired =  BooleanField(
        label='Retired',
        required=False
    )

WitnessFormset = formset_factory(WitnessForm, extra=1)

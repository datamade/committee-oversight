from django.urls import reverse_lazy
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView, TemplateView

from opencivicdata.legislative.models import Event, EventParticipant, EventDocument, EventDocumentLink
from opencivicdata.core.models import Organization

from .utils import save_document
from .models import HearingCategory, WitnessDetails
from .forms import EventForm, CategoryForm, CommitteeForm, WitnessFormset, TranscriptForm

class EventCreate(TemplateView):
    template_name = "create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['event_form'] = EventForm(prefix="event")
        context['committee_form'] = CommitteeForm(prefix="committee")
        context['category_form'] = CategoryForm(prefix="category")
        context['transcript_form'] = TranscriptForm(prefix="transcript")
        context['witness_formset'] = WitnessFormset(prefix="witness")

        return context

    def post(self, request, **kwargs):
        event_form = EventForm(request.POST, prefix="event")
        committee_form = CommitteeForm(request.POST, prefix="committee")
        category_form = CategoryForm(request.POST, prefix="category")
        transcript_form = TranscriptForm(request.POST, prefix="transcript")
        witness_formset = WitnessFormset(request.POST, prefix="witness")

        print("Checking if forms are valid...")

        forms_valid = [event_form.is_valid(), committee_form.is_valid(),
                       category_form.is_valid(), transcript_form.is_valid()]

        if all(forms_valid):
            print("All forms valid! Saving...")

            # save event
            event = event_form.save()

            # find and create committees as EventParticipants
            committees = committee_form.cleaned_data['name']

            for committee in committees:
                name = committee.name
                event = event_form.save(commit=False)
                organization = Organization.objects.get(id=committee.id)
                entity_type = "organization"
                new_committee = EventParticipant(name=name, event=event, organization=organization, entity_type=entity_type)
                new_committee.save()

            # save category
            category = category_form.cleaned_data['category']
            new_category = HearingCategory(event=event, category=category)
            new_category.save()

            # if form includes a transcript URL create EventDocument with original and archived url
            transcript_url = transcript_form.cleaned_data['url']
            save_document(transcript_url, "transcript", event)

            # find and create witnesses
            for witness in witness_formset.cleaned_data:
                name = witness.get('name', None)
                if name:
                    # add witness as EventParticipant
                    entity_type = "person"
                    note = "witness"
                    new_witness = EventParticipant(
                                        name=name,
                                        event=event,
                                        entity_type=entity_type,
                                        note=note)
                    new_witness.save()

                    #save witness statement urls TK
                    witness_url = witness.get('url', None)
                    witness_document = save_document(witness_url, "witness statement", event)

                    #save witness organizations and link to statement urls
                    organization = witness.get('organization', None)
                    new_witness_details = WitnessDetails(
                                        witness=new_witness,
                                        document=witness_document,
                                        organization=organization
                    )
                    new_witness_details.save()

        # eventually this should lead to a list view
        return render(request, 'success.html')

class EventList(ListView):
    model = Event
    template_name = 'list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hearings'] = Event.objects.all().order_by('-created_at')
        return context

# class Success(TemplateView):
#     template_name = 'success.html'
#
# class EventView(DetailView):
#     model = Event
#     template_name = 'detail.html'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         return context

import re

from django.urls import reverse_lazy
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView, DeleteView, TemplateView

from opencivicdata.legislative.models import Event, EventParticipant, EventDocument, EventDocumentLink
from opencivicdata.core.models import Organization
from .forms import EventForm, CommitteeForm, CommitteeMemberForm, WitnessForm, TranscriptForm

class Success(TemplateView):
    template_name = 'success.html'

class EventView(DetailView):
    model = Event
    template_name = 'detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class EventCreate(TemplateView):
    template_name = "create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['event_form'] = EventForm(prefix="event")
        context['committee_form'] = CommitteeForm(prefix="committee")
        context['committeemember_form'] = CommitteeMemberForm(prefix="committeemember")
        context['witness_form'] = WitnessForm(prefix="witness")
        context['transcript_form'] = TranscriptForm(prefix="transcript")

        return context

    def post(self, request, **kwargs):
        event_form = EventForm(request.POST, prefix="event")
        committee_form = CommitteeForm(request.POST, prefix="committee")
        committeemember_form = CommitteeMemberForm(request.POST, prefix="committeemember")
        witness_form = WitnessForm(request.POST, prefix="witness")
        transcript_form = TranscriptForm(request.POST, prefix="transcript")

        print("checking if form is valid...")

        forms_valid = [event_form.is_valid(), committee_form.is_valid(),
                       committeemember_form.is_valid(), witness_form.is_valid(),
                       transcript_form.is_valid()]

        if all(forms_valid):
            print("forms valid! saving...")

            event = event_form.save()

            committees = committee_form.cleaned_data['name']
            for committee in committees:
                name = committee.name
                event = event_form.save(commit=False)
                organization = Organization.objects.get(name=committee.name)
                entity_type = "organization"
                new_committee = EventParticipant(name=name, event=event, organization=organization, entity_type=entity_type)
                new_committee.save()

            committeemembers = committeemember_form.cleaned_data['name'].split(",")
            for committeemember in committeemembers:
                if committeemember == '' or committeemember.isspace():
                    pass
                else:
                    name = committeemember.strip()
                    entity_type = "committee member"
                    new_committeemember = EventParticipant(name=name, event=event, entity_type=entity_type)
                    new_committeemember.save()

            witnesses = witness_form.cleaned_data['name'].split(",")
            for witness in witnesses:
                if witness == '' or witness.isspace():
                    pass
                else:
                    name = witness.strip()
                    entity_type = "person"
                    new_witness = EventParticipant(name=name, event=event, entity_type=entity_type)
                    new_witness.save()

            #TK: set media type; create archive url link
            transcript_url = transcript_form.cleaned_data['url']
            note="transcript"
            new_document = EventDocument(note=note, event=event)
            new_document.save()
            new_document_link = EventDocumentLink(url=transcript_url, document=new_document)
            new_document_link.save()

        return render(request, 'success.html')

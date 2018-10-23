import re

from django.urls import reverse_lazy
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView, DeleteView, TemplateView

from opencivicdata.legislative.models import Event, EventParticipant
from opencivicdata.core.models import Organization
from .forms import EventForm, CommitteeForm, CommitteeMemberForm, WitnessForm

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

        return context

    def post(self, request, **kwargs):
        event_form = EventForm(request.POST, prefix="event")
        committee_form = CommitteeForm(request.POST, prefix="committee")
        committeemember_form = CommitteeMemberForm(request.POST, prefix="committeemember")
        witness_form = WitnessForm(request.POST, prefix="witness")

        print("checking if form is valid...")

        forms_valid = [event_form.is_valid(), committee_form.is_valid(),
                       committeemember_formset.is_valid(), witness_formset.is_valid()]

        if all(forms_valid):
            print("forms valid! saving...")

            event_form.save()

            committees = committee_form.cleaned_data['name']
            for committee in committees:
                name = committee.name
                event = event_form.save(commit=False)
                organization = Organization.objects.get(name=committee.name)
                entity_type = "organization"
                new_committee = EventParticipant(name=name, event=event, organization=organization, entity_type=entity_type)
                new_committee.save()

            committeemembers = committeemember_form.cleaned_data['name']
            for committeemember in committeemembers:
                name = committeemember.name
                event = event_form.save(commit=False)
                entity_type = "committee member"
                new_committeemember = EventParticipant(name=name, event=event, organization=organization, entity_type=entity_type)
                new_committeemember.save()

            witnesses = witness_form.cleaned_data['name']
            for witness in witnesses:
                name = witness.name
                event = event_form.save(commit=False)
                entity_type = "person"
                new_witness = EventParticipant(name=name, event=event, organization=organization, entity_type=entity_type)
                new_witness.save()

        return render(request, 'success.html')

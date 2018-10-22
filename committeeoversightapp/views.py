import re

from django.urls import reverse_lazy
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView, DeleteView, TemplateView

from opencivicdata.legislative.models import Event
from opencivicdata.core.models import Organization
from .forms import EventForm, CommitteeFormset, CommitteeMemberFormset, WitnessFormset

class Success(TemplateView):
    template_name = 'success.html'

class EventView(DetailView):
    model = Event
    template_name = 'detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

# class EventCreate(CreateView):
#     # template_name = 'create.html'
#     #
#     # def get_context_data(self, **kwargs):
#     #     context = super().get_context_data(**kwargs)
#     #
#     #     context['event_form'] = EventForm(prefix="event")
#     #
#     #     if self.request.POST:
#     #         event_form = EventForm(prefix="event")
#     #
#     #         if event_form.is_valid():
#     #             hearing = event_form.save(commit=False)
#     #
#     #             hearing.save()
#     #             return _goto_hearing(hearing)
#     #
#     #     return context
#
#
#     template_name = 'create.html'
#     success_url = reverse_lazy('create-event')
#     form_class = EventForm
#
#     def get_initial(self):
#         initial = super(EventCreate, self).get_initial()
#         jurisdiction = Jurisdiction.objects.get(name='United States of America')
#         initial.update({'jurisdiction': jurisdiction})
#         return initial

class EventCreate(TemplateView):
    template_name = "create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['event_form'] = EventForm(prefix="event")
        context['committee_formset'] = CommitteeFormset(prefix="committee")
        context['committeemember_formset'] = CommitteeMemberFormset(prefix="committeemember")
        context['witness_formset'] = WitnessFormset(prefix="witness")

        return context

    def post(self, request, **kwargs):
        event_form = EventForm(request.POST, prefix="event")
        committee_formset = CommitteeFormset(request.POST, prefix="committee")
        committeemember_formset = CommitteeMemberFormset(request.POST, prefix="committeemember")
        witness_formset = WitnessFormset(request.POST, prefix="witness")

        print("checking if form is valid...")

        forms_valid = [event_form.is_valid(), committee_formset.is_valid(),
                       committeemember_formset.is_valid(), witness_formset.is_valid()]

        if all(forms_valid):
            print("forms valid! saving...")

            event_form.save()

            for committee_form in committee_formset:
                committee = committee_form.save(commit=False)
                committee.event = event_form.save(commit=False)
                committee.organization = Organization.objects.get(name=committee.name)
                committee.save()

            for committeemember_form in committeemember_formset:
                committeemember = committeemember_form.save(commit=False)
                committeemember.event = event_form.save(commit=False)
                committeemember.save()

            for witness_form in witness_formset:
                witness = witness_form.save(commit=False)
                witness.event = event_form.save(commit=False)
                witness.save()

        return render(request, 'success.html')

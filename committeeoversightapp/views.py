import re

from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic.edit import CreateView, DeleteView
from django.views.generic import ListView, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.forms import formset_factory
from django.utils.html import escape

from opencivicdata.legislative.models import Event, EventParticipant, \
                        EventDocument, EventDocumentLink, EventSource
from opencivicdata.core.models import Organization

from django_datatables_view.base_datatable_view import BaseDatatableView

from .utils import save_document, get_document_context, save_witnesses, \
                   save_documents, save_category, save_committees
from .models import HearingCategory, HearingCategoryType, WitnessDetails
from .forms import EventForm, CategoryForm, CommitteeForm, WitnessForm, \
                   WitnessFormset, TranscriptForm, CategoryEditForm, \
                   CommitteeEditForm

import datetime


class EventCreate(LoginRequiredMixin, TemplateView):
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
                       category_form.is_valid(), transcript_form.is_valid(),
                       witness_formset.is_valid()]

        if all(forms_valid):
            print("All forms valid! Saving...")

            # save event
            event = event_form.save()

            save_committees(event, committee_form.cleaned_data['name'])
            save_category(event, category_form.cleaned_data['category'])
            save_documents(event, transcript_form.cleaned_data)
            save_witnesses(event, witness_formset.cleaned_data)

            # save event source
            source = EventSource(event=event, note="web form")
            source.save()

        return redirect('list-event')

class EventList(LoginRequiredMixin, TemplateView):
    template_name = 'list.html'

class EventListJson(BaseDatatableView):
    """ Uses django-datatables-view for server-side DataTable processing."""
    model = Event

    # define the columns that will be returned
    columns = ['updated_at', 'name', 'start_date', 'id', 'id']

    # max number of records returned at a time; protects site from large
    # requests
    max_display_length = 500

    def filter_queryset(self, qs):
        # in order to filter by categories and committees, grab the detail
        # object type and its pk from the ajax url paramenters
        detail_type = self.request.GET.get('detail_type', None)
        id = self.request.GET.get('id', None)

        if detail_type == 'category':
            qs = qs.filter(hearingcategory__category_id=id)
        if detail_type == 'committee':
            pass

        # based on search example at https://pypi.org/project/django-datatables-view/
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(name__icontains=search)

        return qs

    def prepare_results(self, qs):
        json_data = []
        edit_string = "<a href=\"/hearing/edit/{}\"><i class=\"fas fa fa-pencil-alt\" id=\"edit-icon\"></i></a>"
        delete_string = "<a href=\"/hearing/edit/{}\"><i class=\"fas fa fa-times-circle\" id=\"delete-icon\"></i></a>"

        for item in qs:
            json_data.append([
                item.updated_at.strftime("%Y-%m-%d %I:%M%p %Z"),
                item.name,
                item.start_date,
                edit_string.format(escape(item.pk)),
                delete_string.format(escape(item.pk)),
            ])
        return json_data


class EventDelete(LoginRequiredMixin, DeleteView):
    model = Event
    template_name = "delete.html"
    context_object_name = 'hearing'
    success_url = reverse_lazy('list-event')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        #get category context
        try:
            context['category'] = HearingCategory.objects.get(event=context['hearing']).category_id
            context['category_name'] = HearingCategoryType.objects.get(pk=context['category'])
        except ObjectDoesNotExist:
            context['category_name'] = None

        #get committee context
        context['committees'] = context['hearing'].participants.filter(entity_type="organization")

        #get context for documents
        context = get_document_context(context)

        #get context for witnesses
        context['witnesses'] = context['hearing'].participants.filter(note="witness")

        return context

class EventEdit(LoginRequiredMixin, TemplateView):
    template_name = "edit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # retrieve hearing data and prep it to insert into form as initial data
        context['hearing'] = Event.objects.get(id=context['pk'])

        participants = context['hearing'].participants.filter(entity_type='organization').values_list('organization_id', flat=True)

        try:
            hearing_category = context['hearing'].hearingcategory_set.first().category_id
            hearing_category_type = HearingCategoryType.objects.get(id=hearing_category)
        except AttributeError:
            hearing_category_type = None

        witness_list = []
        try:
            witnesses = context['hearing'].participants.filter(note='witness')

            for witness in witnesses:
                witness_dict = {
                    'name': witness.name,
                    'retired': witness.witnessdetails_set.first().retired,
                    'organization': witness.witnessdetails_set.first().organization,
                    'url': witness.witnessdetails_set.first().document.links.exclude(text='archived').first().url
                }

                witness_list.append(witness_dict)

            # reverse the order of the witness list so the formset displays in
            # the order witnesses were entered
            witness_list = list(reversed(witness_list))

        except AttributeError:
            witnessess = None

        context = get_document_context(context)

        # instantiate forms with initial hearing data
        context['event_form'] = EventForm(prefix="event",
                                          initial={'name': context['hearing'].name,
                                                    'start_date': context['hearing'].start_date,
                                                  })
        context['committee_form'] = CommitteeEditForm(prefix="committee",
                                                  initial={'name': Organization.objects.filter(id__in=participants)})
        context['category_form'] = CategoryEditForm(prefix="category",
                                                initial={'category': hearing_category_type})
        context['transcript_form'] = TranscriptForm(prefix="transcript",
                                                    initial={'transcript_url':context['transcript'],
                                                             'opening_statement_chair':context['opening_statement_chair'],
                                                             'opening_statement_rm':context['opening_statement_rm'],
                                                    })

        context['witness_formset'] = WitnessFormset(prefix="witness", initial=witness_list)

        return context

    def post(self, request, **kwargs):
        event_form = EventForm(request.POST, prefix="event")
        committee_form = CommitteeEditForm(request.POST, prefix="committee")
        category_form = CategoryEditForm(request.POST, prefix="category")
        transcript_form = TranscriptForm(request.POST, prefix="transcript")
        witness_formset = WitnessFormset(request.POST, prefix="witness")

        print("Checking if forms are valid...")

        forms_valid = [event_form.is_valid(), committee_form.is_valid(),
                       category_form.is_valid(), transcript_form.is_valid(),
                       witness_formset.is_valid()]

        if all(forms_valid):
            print("All forms valid! Saving...")

            # update event
            event = Event.objects.get(id=self.kwargs['pk'])
            event.name = event_form.cleaned_data['name']
            event.start_date = event_form.cleaned_data['start_date']
            event.save()

            # delete old event data
            EventParticipant.objects.filter(event=event).delete()
            EventDocument.objects.filter(event=event).delete()
            EventDocumentLink.objects.filter(document__event=event).delete()
            HearingCategory.objects.filter(event=event).delete()
            WitnessDetails.objects.filter(witness_id__event=event).delete()

            save_committees(event, committee_form.cleaned_data['name'])
            save_category(event, category_form.cleaned_data['category'])
            save_documents(event, transcript_form.cleaned_data)
            save_witnesses(event, witness_formset.cleaned_data)

        return redirect('list-event')


from django.http import HttpResponse

def pong(request):
    try:
        from .deployment import DEPLOYMENT_ID
    except ImportError:
        return HttpResponse('Bad deployment', status=401)

    return HttpResponse(DEPLOYMENT_ID)

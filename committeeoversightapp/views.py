from django.db.models import Q
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic.edit import DeleteView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import escape

from opencivicdata.legislative.models import Event, EventParticipant, \
                        EventDocument, EventDocumentLink, EventSource
from opencivicdata.core.models import Organization

from django_datatables_view.base_datatable_view import BaseDatatableView

from .utils import get_document_context, save_witnesses, \
                   save_documents, save_category, save_committees
from .models import HearingCategory, HearingCategoryType, WitnessDetails, \
                    CommitteeOrganization, HearingEvent
from .forms import EventForm, CategoryForm, CommitteeForm, \
                   WitnessFormset, TranscriptForm, CategoryEditForm, \
                   CommitteeEditForm


class EventCreate(LoginRequiredMixin, TemplateView):
    template_name = "hearing_create.html"

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

        return redirect('/hearings')


class EventList(LoginRequiredMixin, TemplateView):
    template_name = 'hearing_list.html'


class EventListJson(BaseDatatableView):
    """ Uses django-datatables-view for server-side DataTable processing."""
    model = HearingEvent

    # Define the columns that will be returned. These need to match attributes
    # of the model but most will be calculated later, so 'id' here is a
    # placeholder.
    columns = [
        'start_date',
        'name',
        'id', # committees
        'id', # category
        'id', # edit
        'id', # delete
    ]

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
            qs = qs.filter(
                Q(participants__organization_id=id) |
                Q(participants__organization__parent_id=id)
            )

        # based on search example at
        # https://pypi.org/project/django-datatables-view/
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(name__icontains=search)

        return qs

    def prepare_results(self, qs):
        json_data = []
        detail_string = "<a href=\"{0}\">{1}</a>"
        edit_string = "<a href=\"{}\"><i class=\"fas fa fa-pencil-alt\" id=\"edit-icon\"></i></a>"
        delete_string = "<a href=\"{}\"><i class=\"fas fa fa-times-circle\" id=\"delete-icon\"></i></a>"

        for item in qs:
            committees = set()
            for committee in item.committees:
                if committee.is_subcommittee:
                    committee_string = detail_string.format(
                        escape(committee.parent_url),
                        escape(committee.parent)
                    )
                else:
                    committee_string = detail_string.format(
                        escape(committee.url),
                        escape(committee.name)
                    )
                committees.add(committee_string)

            category_string = ''
            if item.category:
                category_string = detail_string.format(
                                    escape(item.category.url),
                                    escape(item.category.name)
                                )

            row_data = [
                item.start_date,
                detail_string.format(
                    escape(reverse_lazy(
                        'detail-event',
                        kwargs={'pk':item.pk}
                    )),
                    escape(item.name.title())
                ),
                ', '.join(committees),
                category_string
            ]

            if self.request.user.is_authenticated:
                row_data += [
                    edit_string.format(
                        escape(reverse_lazy(
                            'edit-event',
                            kwargs={'pk':item.pk}
                        ))
                    ),
                    delete_string.format(
                        escape(reverse_lazy(
                            'delete-event',
                            kwargs={'pk':item.pk}
                        ))
                    ),
                ]
            else:
                row_data += ['', '']

            json_data.append(row_data)

        return json_data


class EventDetail(DetailView):
    model = HearingEvent
    template_name = "hearing_detail.html"
    context_object_name = 'hearing'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['category'] = context['hearing'].category
        context['committees'] = context['hearing'].committees
        context = get_document_context(context)
        context['witnesses'] = context['hearing'].participants.filter(
            note="witness"
        )

        return context


class EventDelete(LoginRequiredMixin, DeleteView):
    model = Event
    template_name = "hearing_delete.html"
    context_object_name = 'hearing'
    success_url = '/hearings'


class EventEdit(LoginRequiredMixin, TemplateView):
    template_name = "hearing_edit.html"

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

        return redirect('/hearings')


from django.http import HttpResponse

def pong(request):
    try:
        from .deployment import DEPLOYMENT_ID
    except ImportError:
        return HttpResponse('Bad deployment', status=401)

    return HttpResponse(DEPLOYMENT_ID)

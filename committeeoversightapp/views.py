from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic.edit import CreateView, DeleteView
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist

from opencivicdata.legislative.models import Event, EventParticipant, EventDocument, EventDocumentLink, EventSource
from opencivicdata.core.models import Organization

from .utils import save_document
from .models import HearingCategory, HearingCategoryType, WitnessDetails
from .forms import EventForm, CategoryForm, CommitteeForm, WitnessFormset, TranscriptForm

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
            documents = [('transcript_url', "transcript"), ('opening_statement_chair', "chair opening statement"), ('opening_statement_rm', "ranking member opening statement")]

            for (field, note) in documents:
                url = transcript_form.cleaned_data[field]
                save_document(url, note, event)

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
                                        note=note
                    )
                    new_witness.save()

                    #save witness statement urls TK
                    witness_url = witness.get('url', None)
                    witness_document = save_document(witness_url, "witness statement", event)

                    #save witness organizations and link to statement urls
                    organization = witness.get('organization', None)
                    retired = witness.get('retired', False)
                    new_witness_details = WitnessDetails(
                                        witness=new_witness,
                                        document=witness_document,
                                        organization=organization,
                                        retired=retired
                    )
                    new_witness_details.save()

            # save event source
            source = EventSource(event=event, note="web form")
            source.save()

        return redirect('list-event')

class EventList(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'list.html'
    context_object_name = 'hearings'
    queryset = Event.objects.all().order_by('-created_at')[:500]

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
        eventdocuments_qs = EventDocument.objects.filter(event_id=context['hearing'])

        document_types = {'transcript':'transcript', 'opening_statement_chair':'chair opening statement', 'opening_statement_rm':'ranking member opening statement'}

        for key, value in document_types.items():
            try:
                doc = eventdocuments_qs.get(note=value)
                context[key] = EventDocumentLink.objects.exclude(text='archived').filter(document_id=doc)[0].url
                context[key + '_archived'] = EventDocumentLink.objects.get(document_id=doc, text='archived').url
            except ObjectDoesNotExist:
                pass

        #get context for witnesses
        context['witnesses'] = context['hearing'].participants.filter(note="witness")

        return context


from django.http import HttpResponse

def pong(request):
    try:
        from .deployment import DEPLOYMENT_ID
    except ImportError:
        return HttpResponse('Bad deployment', status=401)

    return HttpResponse(DEPLOYMENT_ID)

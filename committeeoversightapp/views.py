from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic.edit import CreateView, DeleteView
from django.views.generic import ListView, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist

from opencivicdata.legislative.models import Event, EventParticipant, EventDocument, EventDocumentLink, EventSource
from opencivicdata.core.models import Organization

from .utils import save_document, get_document_context
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
    queryset = Event.objects.all().order_by('-updated_at')[:500]

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
                }

                try:
                    witness_dict['organization'] = witness.witnessdetails_set.first().organization
                except:
                    pass

                try:
                    witness_dict['url'] = witness.witnessdetails_set.first().document.links.exclude(text='archived').first().url
                except:
                    pass

                witness_list.append(witness_dict)

        except AttributeError:
            witnessess = None

        context = get_document_context(context)

        context['event_form'] = EventForm(prefix="event",
                                          initial={'name': context['hearing'].name,
                                                    'start_date': context['hearing'].start_date,
                                                  })
        context['committee_form'] = CommitteeForm(prefix="committee",
                                                  initial={'name': Organization.objects.filter(id__in=participants)})
        context['category_form'] = CategoryForm(prefix="category",
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
        committee_form = CommitteeForm(request.POST, prefix="committee")
        category_form = CategoryForm(request.POST, prefix="category")
        transcript_form = TranscriptForm(request.POST, prefix="transcript")
        witness_formset = WitnessFormset(request.POST, prefix="witness")

        print("Checking if forms are valid...")

        forms_valid = [event_form.is_valid(), committee_form.is_valid(),
                       category_form.is_valid(), transcript_form.is_valid()]

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

            # find and create committees as EventParticipants
            committees = committee_form.cleaned_data['name']
            print(committees)

            for committee in committees:
                name = committee.name
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

        return redirect('list-event')


from django.http import HttpResponse

def pong(request):
    try:
        from .deployment import DEPLOYMENT_ID
    except ImportError:
        return HttpResponse('Bad deployment', status=401)

    return HttpResponse(DEPLOYMENT_ID)

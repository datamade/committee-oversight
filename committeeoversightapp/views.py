import re
import threading
import requests
from os.path import splitext
from urllib.parse import urlparse

from django.urls import reverse_lazy
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView, DeleteView, TemplateView

from opencivicdata.legislative.models import Event, EventParticipant, EventDocument, EventDocumentLink
from opencivicdata.core.models import Organization

from .models import HearingCategory
from .forms import EventForm, CategoryForm, CommitteeForm, WitnessFormset, TranscriptForm

class Success(TemplateView):
    template_name = 'success.html'

class EventView(DetailView):
    model = Event
    template_name = 'detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

# given a url string, find the file extension at the end
def get_ext(url):
    path = urlparse(url).path
    ext = splitext(path)[1]
    return ext

# archive a url string
def archive_url(url):
    wayback_host = 'http://web.archive.org'
    save_url = '{0}/save/{1}'.format(wayback_host, url)
    archived = requests.get(save_url)
    archive_url = '{0}{1}'.format(wayback_host, archived.headers['Content-Location'])
    return archive_url

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
                       category_form.is_valid(), witness_formset.is_valid(),
                       transcript_form.is_valid()]

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

            if transcript_url == '' or witness.isspace():
                pass
            else:
                note="transcript"
                new_document = EventDocument(note=note, event=event)
                new_document.save()

                archived_transcript_url = archive_url(transcript_url)

                extensions = {'.pdf': 'application/pdf', '.htm': 'text/html', '.html': 'text/html'}
                ext = get_ext(transcript_url)
                media_type = extensions.get(ext.lower(), '')

                new_document_link = EventDocumentLink(
                                        url=transcript_url,
                                        document=new_document,
                                        media_type=media_type
                                    )
                new_archived_document_link = EventDocumentLink(
                                        url=archived_transcript_url,
                                        document=new_document,
                                        media_type=media_type
                                    )

                new_document_link.save()
                new_archived_document_link.save()

            # find and create witnesses as EventParticipants
            for witness in witness_formset:
                print(witness)
            # witnesses = witness_formset.cleaned_data['name'].split(",")
            #
            # for witness in witnesses:
            #     if witness == '' or witness.isspace():
            #         pass
            #     else:
            #         name = witness.strip()
            #         entity_type = "person"
            #         new_witness = EventParticipant(name=name, event=event, entity_type=entity_type)
            #         new_witness.save()

        # eventually this should lead to a list view
        return render(request, 'success.html')

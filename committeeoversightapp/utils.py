import requests
from os.path import splitext
from urllib.parse import urlparse

from django.core.exceptions import ObjectDoesNotExist

from opencivicdata.legislative.models import EventDocument, EventDocumentLink, \
                                             EventParticipant
from opencivicdata.core.models import Organization
from .models import WitnessDetails, HearingCategory

def get_ext(url):
    """ Given a url string, find the file extension at the end """
    
    path = urlparse(url).path
    ext = splitext(path)[1]
    return ext

def archive_url(url):
    wayback_host = 'http://web.archive.org'
    save_url = '{0}/save/{1}'.format(wayback_host, url)
    archived = requests.get(save_url)
    try:
        archive_url = '{0}{1}'.format(wayback_host, archived.headers['Content-Location'])
        return archive_url
    except KeyError:
        return None

def save_document(url, note, event):
    if url == '' or url.isspace() or url is None:
        return None
    else:
        new_document = EventDocument(note=note, event=event)
        new_document.save()

        archived_url = archive_url(url)

        extensions = {'.pdf': 'application/pdf', '.htm': 'text/html', '.html': 'text/html'}
        ext = get_ext(url)
        media_type = extensions.get(ext.lower(), '')

        new_document_link = EventDocumentLink(
                                url=url,
                                document=new_document,
                                media_type=media_type,
                            )
        new_document_link.save()

        if archived_url:
            new_archived_document_link = EventDocumentLink(
                                    url=archived_url,
                                    document=new_document,
                                    media_type=media_type,
                                    text="archived"
                                )
            new_archived_document_link.save()

        return new_document

def get_document_context(context):
    """ Lugar staff will be entering and editing URLs for the following 3
    document types, and should be editable in their original form but
    also saved as archived links """

    document_types = {'transcript':'transcript',
                      'opening_statement_chair':'chair opening statement',
                      'opening_statement_rm':'ranking member opening statement'}

    eventdocuments_qs = EventDocument.objects.filter(event_id=context['hearing'])

    for key, value in document_types.items():
        try:
            doc = eventdocuments_qs.get(note=value)
            context[key] = EventDocumentLink.objects.exclude(text='archived').filter(document_id=doc)[0].url
        except (ObjectDoesNotExist):
            context[key] = None

        try:
            context[key + '_archived'] = EventDocumentLink.objects.get(document_id=doc, text='archived').url
        except (ObjectDoesNotExist, UnboundLocalError):
            pass

    return context

def save_witnesses(event, witnesses):
    for witness in witnesses:
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

def save_documents(event, transcript_data):
    """ Create EventDocument with original and archived url if form includes a
    transcript URL """

    documents = [('transcript_url', "transcript"), ('opening_statement_chair', "chair opening statement"), ('opening_statement_rm', "ranking member opening statement")]

    for (field, note) in documents:
        url = transcript_data[field]
        save_document(url, note, event)

def save_category(event, category):
    if category is not None:
        new_category = HearingCategory(event=event, category=category)
        new_category.save()

def save_committees(event, committees):
    """Find and create committees as EventParticipants"""

    for committee in committees:
        name = committee.name
        organization = Organization.objects.get(id=committee.id)
        entity_type = "organization"
        new_committee = EventParticipant(name=name, event=event, organization=organization, entity_type=entity_type)
        new_committee.save()

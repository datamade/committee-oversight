import requests
from os.path import splitext
from urllib.parse import urlparse

from django.core.exceptions import ObjectDoesNotExist

from opencivicdata.legislative.models import EventDocument, EventDocumentLink

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
    document_types = {'transcript':'transcript', 'opening_statement_chair':'chair opening statement', 'opening_statement_rm':'ranking member opening statement'}

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

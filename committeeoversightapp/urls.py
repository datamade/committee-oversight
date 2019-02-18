from django.conf.urls import url, include
from committeeoversightapp.views import EventCreate, EventList, EventDelete, \
                                        EventEdit

urlpatterns = [
    url(r'accounts/', include('django.contrib.auth.urls')),
    url(r'^$', EventCreate.as_view(), name='create-event'),
    url(r'^list$', EventList.as_view(), name='list-event'),
    url(r'^delete/(?P<pk>.*?/.*?)/', EventDelete.as_view(), name="delete-event"),
    url(r'^edit/(?P<pk>.*?/.*?)/', EventEdit.as_view(), name="edit-event"),
]

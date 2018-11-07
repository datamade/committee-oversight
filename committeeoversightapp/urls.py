from django.conf.urls import url, include
from committeeoversightapp.views import EventCreate, EventList

urlpatterns = [
    # url(r'^view/(?P<pk>\d+)$', EventView.as_view(), name="view-event")
    url(r'accounts/', include('django.contrib.auth.urls')),
    url(r'^$', EventCreate.as_view(), name='create-event'),
    url(r'^list$', EventList.as_view(), name='list-event'),
    # url(r'^view/(?P<pk>\d+)$', EventView.as_view(), name="view-event"),
    # url(r'^success/$', Success.as_view(), name='success'),
]

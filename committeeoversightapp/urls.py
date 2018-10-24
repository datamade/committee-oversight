from django.conf.urls import url, include
from committeeoversightapp.views import EventView, EventCreate, Success

urlpatterns = [
    # url(r'^view/(?P<pk>\d+)$', EventView.as_view(), name="view-event")
    url(r'^$', EventCreate.as_view(), name='create-event'),
    url(r'^success/$', Success.as_view(), name='success'),
    url(r'^select2/', include('django_select2.urls')),
    # url(r'^$', EventList.as_view(), name='list-event'),
]

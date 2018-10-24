from django.conf.urls import url, include
from committeeoversightapp.views import EventList, EventCreate

urlpatterns = [
    # url(r'^view/(?P<pk>\d+)$', EventView.as_view(), name="view-event")
    url(r'^$', EventCreate.as_view(), name='create-event'),
    url(r'^list$', EventList.as_view(), name='list-event'),
]

from django.conf.urls import url, include
from committeeoversightapp.views import EventCreate, EventList, EventDelete, \
                                        EventEdit, EventListJson

urlpatterns = [
    url(r'accounts/', include('django.contrib.auth.urls')),
    url(r'^hearing/create/$', EventCreate.as_view(), name='create-event'),
    url(r'^hearing/list$', EventList.as_view(), name='list-event'),
    url(r'^hearing/delete/(?P<pk>.*?/.*?)/', EventDelete.as_view(), name="delete-event"),
    url(r'^hearing/edit/(?P<pk>.*?/.*?)/', EventEdit.as_view(), name="edit-event"),
    url(r'^my/datatable/data/(?P<detail_type>.*?)$', EventListJson.as_view(), name='order_list_json')
]

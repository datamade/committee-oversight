from django.urls import include, path, re_path
from committeeoversightapp.views import EventCreate, EventList, EventDelete, \
                                        EventEdit, EventListJson, EventDetail

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('hearing/create/', EventCreate.as_view(), name='create-event'),
    re_path(r'^hearing/view/(?P<pk>.*?/.*?)/', EventDetail.as_view(), name="detail-event"),
    re_path(r'^hearing/delete/(?P<pk>.*?/.*?)/', EventDelete.as_view(), name="delete-event"),
    re_path(r'^hearing/edit/(?P<pk>.*?/.*?)/', EventEdit.as_view(), name="edit-event"),
    path('my/datatable/data/', EventListJson.as_view(), name='order_list_json')
]

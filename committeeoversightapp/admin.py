from django.contrib import admin

from committeeoversightapp.models import CommitteeOrganization, CommitteeDetailPage


class HiddenAdminMixin:
    def has_module_permission(self, request):
        '''
        Override to exclude from admin interface:
        https://stackoverflow.com/a/49295987/7142170
        '''
        return False


class CommitteeOrganizationAdmin(HiddenAdminMixin, admin.ModelAdmin):
    '''
    Define this admin in order to take advantage of the Select2 mixin in the
    CommitteeDetailPage Wagtail interface.
    '''
    ordering = ('name',)
    search_fields = ('name',)

    def get_queryset(self, request):
        return CommitteeOrganization.objects.congressional_committees()


class CommitteeDetailPageAdmin(HiddenAdminMixin, admin.ModelAdmin):
    '''
    Ditto CommitteeOrganizationAdmin docstring.
    '''
    autocomplete_fields = ('committee',)


admin.site.register(CommitteeOrganization, CommitteeOrganizationAdmin)
admin.site.register(CommitteeDetailPage, CommitteeDetailPageAdmin)

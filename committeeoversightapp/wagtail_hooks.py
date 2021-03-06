from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.html import format_html_join, format_html

from wagtail.core import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin, modeladmin_register)

from .models import Congress


@hooks.register('insert_editor_js')
def editor_js():
    js_files = [
        'js/detail_editor_slug.js',
    ]
    js_includes = format_html_join('\n', '<script src="{0}{1}"></script>',
        ((settings.STATIC_URL, filename) for filename in js_files)
    )

    return js_includes

@hooks.register("insert_global_admin_css", order=100)
def global_admin_css():
    """Add /static/css/custom.css to the admin."""
    return format_html(
        '<link rel="stylesheet" href="{}">',
        static("css/wagtail-overrides.css")
    )

class CongressAdmin(ModelAdmin):
    model = Congress
    menu_label = 'Edit Congresses'
    menu_icon = 'date'
    menu_order = 000
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        'id',
        'start_date',
        'end_date',
        'inactive_days',
        'footnote'
    )
    list_filter = ()
    search_fields = ('id', 'footnote')


modeladmin_register(CongressAdmin)

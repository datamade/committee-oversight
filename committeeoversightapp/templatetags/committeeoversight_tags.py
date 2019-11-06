from django import template
from slugify import slugify

from committeeoversightapp.models import CommitteeOrganization

register = template.Library()


@register.filter
def get_category_url(category):
    try:
        return '/category-' + slugify(category.name)
    except AttributeError:
        return None


@register.filter
def get_committee_url(committee):
    return '/' + CommitteeOrganization.objects.get(id=committee.id).url_id()


@register.filter
def is_subcommittee(committee):
    chambers = [
        'United States House of Representatives',
        'United States Senate'
        ]

    if committee.parent.name in chambers:
        return False
    else:
        return True

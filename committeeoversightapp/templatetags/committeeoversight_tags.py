from django import template

register = template.Library()


@register.filter(name='lookup')
def lookup(value, arg):
    return value[arg]


rating_colors = {
    'A+': 'a-plus-rating',
    'A': 'a-rating',
    'A-': 'a-minus-rating',
    'B+': 'b-plus-rating',
    'B': 'b-rating',
    'B-': 'b-minus-rating',
    'C+': 'c-plus-rating',
    'C': 'c-rating',
    'C-': 'c-minus-rating',
    'D+': 'f-plus-rating',
    'D': 'f-rating',
    'D-': 'f-minus-rating',
    'F+': 'f-rating',
    'F': 'f-rating',
    'F-': 'f-rating'
}


@register.filter(name='rating_to_color')
def rating_to_color(value):
    return rating_colors[value]

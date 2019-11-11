import re

from django.utils.text import slugify
from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.humanize.templatetags.humanize import ordinal
from django.db import models
from django.db.models.fields import TextField, BooleanField

from wagtail.core.models import Page
from wagtail.core.fields import StreamField, RichTextField
from wagtail.core import blocks
from wagtail.admin.edit_handlers import StreamFieldPanel, MultiFieldPanel, \
                                        FieldPanel
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.blocks import ImageChooserBlock

from opencivicdata.core.models import Organization
from opencivicdata.legislative.models import Event, EventParticipant, \
                                             EventDocument



class CommitteeManager(models.Manager):

    def congressional_committees(self):
        return self.get_queryset().filter(
            classification='committee',
            parent_id__name__in=(
                'United States House of Representatives',
                'United States Senate'
            )
        ).order_by('name')


class CommitteeOrganization(Organization):
    class Meta:
        proxy = True

    objects = CommitteeManager()

    CHAMBERS = [
        'United States House of Representatives',
        'United States Senate'
        ]

    @property
    def url(self):
        """
        Get a committee's url slug.

        Since Wagtail strips slashes out of urls but OCD prefixes their orgs
        with 'ocd-organization/', we need to do some cleaning. The url
        of each committee should be of the form 'committee-<committee #>'
        """
        return '/committee-' + self.id.split('ocd-organization/').pop()

    @property
    def parent_url(self):
        return '/committee-' + self.parent.id.split('ocd-organization/').pop()

    @property
    def latest_rating(self):
        """
        Return the committee's rating for the most recent Congress.
        """
        rating_set = self.committeerating_set.order_by('-congress')
        return rating_set[0]

    @property
    def short_name(self):
        if self.parent.name in self.CHAMBERS:
            return re.sub(r'(House|Senate) Committee on ', '', self.name)
        return self.name

    @property
    def is_subcommittee(self):
        if self.parent.parent.name in self.CHAMBERS:
            return True
        else:
            return False

    @property
    def chair(self):
        return CommitteeDetailPage.objects.get(committee=self.id).chair

    @property
    def hide_rating(self):
        return CommitteeDetailPage.objects.get(committee=self.id).hide_rating

    def __str__(self):
        return self.name


class HearingCategoryType(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100, primary_key=False)

    @property
    def url(self):
        try:
            return '/category-' + slugify(self.name)
        except AttributeError:
            return None

    def __str__(self):
        return self.name


class HearingCategory(models.Model):
    event = models.ForeignKey(Event, null=True, on_delete=models.CASCADE)
    category = models.ForeignKey(HearingCategoryType,
                                 null=True,
                                 on_delete=models.CASCADE)


class WitnessDetails(models.Model):
    witness = models.ForeignKey(EventParticipant, on_delete=models.CASCADE)
    document = models.ForeignKey(EventDocument,
                                 null=True,
                                 blank=True,
                                 on_delete=models.CASCADE)
    organization = models.CharField(max_length=100,
                                    null=True,
                                    blank=True,
                                    primary_key=False)
    retired = models.BooleanField(default=False)


class Committee(models.Model):
    """
    Used in the import_data management command, not the frontend app.
    """

    lugar_id = models.IntegerField(null=True, blank=True, primary_key=False)
    lugar_name = models.CharField(max_length=200,
                                  null=True,
                                  blank=True,
                                  primary_key=False)
    organization = models.ForeignKey(Organization,
                                     null=True,
                                     blank=True,
                                     on_delete=models.CASCADE)


class CommitteeRating(models.Model):
    committee = models.ForeignKey(Organization, on_delete=models.CASCADE)
    congress = models.IntegerField()
    rating = models.CharField(max_length=100)

    @property
    def congress_label(self):
        '''
        116 => '116th Congress'
        '''
        return '{} Congress'.format(ordinal(self.congress))

    @property
    def css_class(self):
        '''
        A+ => 'a-plus-rating'
        '''

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
            'D+': 'd-plus-rating',
            'D': 'd-rating',
            'D-': 'd-minus-rating',
            'F+': 'f-rating',
            'F': 'f-rating',
            'F-': 'f-rating'
        }

        return rating_colors[self.rating]

    def __str__(self):
        return self.rating


class StaticPage(Page):
    featured_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    body = StreamField([
        ('heading', blocks.CharBlock(classname='full title', icon='openquote')),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('button',
         blocks.StructBlock([
            ('button_text', blocks.CharBlock()),
            ('button_link', blocks.URLBlock())
            ],
         icon='site'))
    ])

    # Editor configuration
    content_panels = Page.content_panels + [
        ImageChooserPanel('featured_image'),
        StreamFieldPanel('body'),
    ]

class LandingPage(Page):
    body = RichTextField()

    # Editor configuration
    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    def get_context(self, request):
        context = super(LandingPage, self).get_context(request)

        congressional_committees = CommitteeOrganization.objects.congressional_committees()

        context['house_committees'] = congressional_committees.filter(
            parent__name='United States House of Representatives'
        )
        context['senate_committees'] = congressional_committees.filter(
            parent__name='United States Senate'
        )

        context['committees'] = congressional_committees

        return context


class DetailPage(Page):
    '''
    Model page method adapted from
    https://timonweb.com/tutorials/how-to-hide-and-auto-populate-title-field-of-a-page-in-wagtail-cms/
    User-entered and -editable data should live as attributes on a model's DetailPage;
    scraped or OCD-sourced data should be attached to the corresponding base model
    '''

    class Meta:
        abstract = True

    @property
    def title_field(self):
        raise NotImplementedError('title_field must be defined on child classes')

    body = RichTextField()

    def save(self, *args, **kwargs):
        title = str(getattr(self, self.title_field))
        for attr in ('title', 'draft_title'):
            setattr(self, attr, title)
        super().save(*args, **kwargs)


class CategoryDetailPage(DetailPage):

    title_field = 'category'

    category = models.ForeignKey(
        HearingCategoryType,
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Select a category for this page."
    )

    content_panels = [
        FieldPanel('category'),
        FieldPanel('body'),
    ]


class CommitteeDetailPage(DetailPage):
    title_field = 'committee'

    committee = models.ForeignKey(
        CommitteeOrganization,
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Select a committee for this page."
    )

    chair = TextField(blank=True, null=True)

    hide_rating = BooleanField(default=False)

    content_panels = [
        FieldPanel('committee', widget=AutocompleteSelect(committee.remote_field, admin.site)),
        FieldPanel('body'),
        FieldPanel('chair'),
        FieldPanel('hide_rating'),
    ]

class HearingListPage(Page):
    body = RichTextField()

    # Editor configuration
    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    def get_context(self, request):
        context = super(HearingListPage, self).get_context(request)
        context['categories'] = HearingCategoryType.objects.all()
        return context

from django.contrib.humanize.templatetags.humanize import ordinal
from django.db import models

from wagtail.core.models import Page
from wagtail.core.fields import StreamField, RichTextField
from wagtail.core import blocks
from wagtail.admin.edit_handlers import StreamFieldPanel, MultiFieldPanel, \
                                        FieldPanel
from wagtail.images.blocks import ImageChooserBlock

from opencivicdata.core.models import Organization
from opencivicdata.legislative.models import Event, EventParticipant, \
                                             EventDocument


class CommitteeOrganization(Organization):
    class Meta:
        proxy = True

    def url_id(self):
        """
        Since Wagtail strips slashes out of urls but OCD prefixes their orgs
        with 'ocd-organization/', we need to do some cleaning. The url_id
        of each committee should be of the form 'committee-<committee #>'
        """
        url_id = 'committee-' + self.id.split('ocd-organization/').pop()
        return url_id

    def latest_rating(self):
        """
        Return the committee's rating for the most recent Congress.
        """
        rating_set = self.committeerating_set.order_by('-congress')
        return rating_set[0]


class HearingCategoryType(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100, primary_key=False)

    def __str__(self):
        return u'({0}) {1}'.format(self.id, self.name)


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
        context['house_committees'] = CommitteeOrganization.objects.all().filter(
                                    classification='committee'
                                ).filter(
                                    parent_id__name__in=['United States House of Representatives']
                                )
        context['senate_committees'] = CommitteeOrganization.objects.all().filter(
                                    classification='committee',
                                    parent_id__name__in=['United States Senate']
                                )

        committees = context['house_committees'] | context['senate_committees']
        context['committees'] = committees.order_by('name')

        print("helskdjlfksgj")
        print(dir(context['committees'].first()))

        return context



class CategoryDetailPage(Page):
    # model page method adapted from https://timonweb.com/tutorials/how-to-hide-and-auto-populate-title-field-of-a-page-in-wagtail-cms/
    category = models.ForeignKey(
        HearingCategoryType,
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Select a category for this page."
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
    content_panels = [
        FieldPanel('category'),
        StreamFieldPanel('body'),
    ]

    def save(self, *args, **kwargs):
        print("saving now...")
        self.title = "Category " + self.category.id + ": " + self.category.name
        self.draft_title = self.title
        super().save(*args, **kwargs)

from django.db import models

from wagtail.core.models import Page
from wagtail.core.fields import StreamField
from wagtail.core import blocks
from wagtail.admin.edit_handlers import StreamFieldPanel, MultiFieldPanel, \
                                        FieldPanel
from wagtail.images.blocks import ImageChooserBlock

from opencivicdata.core.models import Organization
from opencivicdata.legislative.models import Event, EventParticipant, \
                                             EventDocument


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
    lugar_id = models.IntegerField(null=True, blank=True, primary_key=False)
    lugar_name = models.CharField(max_length=200,
                                  null=True,
                                  blank=True,
                                  primary_key=False)
    organization = models.ForeignKey(Organization,
                                     null=True,
                                     blank=True,
                                     on_delete=models.CASCADE)


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
    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Page configuration"),
    ]


class CategoryDetailPage(Page):
    # model page method adapted from https://timonweb.com/tutorials/how-to-hide-and-auto-populate-title-field-of-a-page-in-wagtail-cms/
    detail_object = models.ForeignKey(
        HearingCategoryType,
        blank=False,
        null=True,
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
    content_panels = [
        FieldPanel('detail_object'),
        StreamFieldPanel('body'),
    ]
    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Page configuration"),
    ]

    def save(self, *args, **kwargs):
        print("saving now...")
        self.title = "Category " + self.detail_object.id + ": " + self.detail_object.name
        self.draft_title = self.title
        super().save(*args, **kwargs)

import re
from datetime import date

from django.utils.text import slugify
from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.humanize.templatetags.humanize import ordinal
from django.db import models
from django.db.models import Max, Avg
from django.db.models.fields import TextField, BooleanField
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

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


class HearingEvent(Event):
    class Meta:
        proxy = True

    @property
    def category(self):
        try:
            return HearingCategory.objects.get(
                event_id=self.id
            ).category
        except ObjectDoesNotExist:
            return None

    @property
    def committees(self):
        return CommitteeOrganization.objects.filter(
            eventparticipant__event=self.id
        )

class CommitteeManager(models.Manager):
    def permanent_committees(self):
        return self.get_queryset().filter(
            classification='committee',
            name__in=settings.CURRENT_PERMANENT_COMMITTEES
        ).order_by('name')

    def house_committees(self):
        return self.permanent_committees().filter(
            parent__name='United States House of Representatives'
        )

    def senate_committees(self):
        return self.permanent_committees().filter(
            parent__name='United States Senate'
        )

    def get_committee_context(self, context):
        context['committees'] = self.permanent_committees()
        context['house_committees'] = self.house_committees()
        context['senate_committees'] = self.senate_committees()
        return context


class CommitteeOrganization(Organization):
    class Meta:
        proxy = True

    objects = CommitteeManager()

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
    def short_name(self):
        if self.parent.name in settings.CHAMBERS:
            return re.sub(r'(House|Senate) Committee on ', '', self.name)
        return self.name

    @property
    def is_subcommittee(self):
        if self.parent.parent.name in settings.CHAMBERS:
            return True
        else:
            return False

    @property
    def chair(self):
        return CommitteeDetailPage.objects.get(committee=self.id).chair

    @property
    def hide_rating(self):
        return CommitteeDetailPage.objects.get(committee=self.id).hide_rating

    @property
    def ratings_by_congress_desc(self):
        return self.committeerating_set.all().order_by('-congress__id')

    @property
    def ratings_by_congress_asc(self):
        return self.committeerating_set.all().order_by('congress__id')

    @property
    def latest_rating(self):
        return self.ratings_by_congress_desc[0]

    @property
    def max_chp_points(self):
        return self.ratings_by_congress_desc.aggregate(
            Max('chp_points')
        )['chp_points__max']

    @property
    def investigative_oversight_hearings_max(self):
        return self.get_max_rating('investigative_oversight_hearings')

    @property
    def policy_legislative_hearings_max(self):
        return self.get_max_rating('policy_legislative_hearings')

    @property
    def total_hearings_max(self):
        return self.get_max_rating('total_hearings')

    @property
    def investigative_oversight_hearings_avg(self):
        return self.get_avg_rating('investigative_oversight_hearings')

    @property
    def policy_legislative_hearings_avg(self):
        return self.get_avg_rating('policy_legislative_hearings')

    @property
    def total_hearings_avg(self):
        return self.get_avg_rating('total_hearings')

    def get_avg_rating(self, hearing_type):
        return round(self.ratings_by_congress_desc \
            .aggregate(
                Avg(hearing_type)
            )[hearing_type + '__avg'], 1)

    def get_max_rating(self, hearing_type):
        return round(self.ratings_by_congress_desc \
            .aggregate(
                Max(hearing_type)
            )[hearing_type + '__max'], 1)

    def __str__(self):
        return self.name


class Congress(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()

    @property
    def label(self):
        '''
        116 => '116th Congress'
        '''
        return '{} Congress'.format(ordinal(self.id))

    @property
    def is_current(self):
        if self.start_date < date.today() < self.end_date:
            return True
        else:
            return False

    @property
    def percent_passed(self):
        days_in_session = 668
        days_passed = (date.today() - self.start_date).days
        percent_passed = int(round(days_passed / days_in_session * 100))

        if percent_passed <= 100:
            return percent_passed
        else:
            return 100

    def __str__(self):
        return self.label


class CommitteeRating(models.Model):
    committee = models.ForeignKey(CommitteeOrganization, on_delete=models.CASCADE)
    congress = models.ForeignKey(Congress, on_delete=models.CASCADE)
    investigative_oversight_hearings = models.IntegerField(null=True, blank=True)
    policy_legislative_hearings = models.IntegerField(null=True, blank=True)
    total_hearings = models.IntegerField(null=True, blank=True)
    chp_points = models.IntegerField(null=True, blank=True)

    @property
    def chp_score(self):
        try:
            current_score = self.chp_points \
                / self.committee.max_chp_points * 100

            if not self.congress.is_current:
                return int(round(current_score))
            else:
                return int(round(current_score / self.congress.percent_passed \
                    * 100))

        except ZeroDivisionError:
            print("Divide by zero error on " + self.committee.name)
            return 0

    @property
    def chp_grade(self):
        score = self.chp_score
        if 92 <= score:
            return 'A'
        elif 90 <= score < 92:
            return 'A-'
        elif 88 <= score < 90:
            return 'B+'
        elif 82 <= score < 88:
            return 'B'
        elif 80 <= score < 82:
            return 'B-'
        elif 78 <= score < 80:
            return 'C+'
        elif 72 <= score < 78:
            return 'C'
        elif 70 <= score < 72:
            return 'C-'
        elif 68 <= score < 70:
            return 'D+'
        elif 62 <= score < 68:
            return 'D'
        elif 60 <= score < 62:
            return 'D-'
        elif 0 <= score < 60:
            return 'F'
        else:
            return 'C'

    @property
    def css_class(self):
        '''
        A+ => 'a-plus-rating'
        '''

        rating_colors = {
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
            'F': 'f-rating'
        }

        return rating_colors[self.chp_grade]

    @property
    def investigative_oversight_percent_max(self):
        return self.get_percent_max('investigative_oversight_hearings')

    @property
    def policy_legislative_percent_max(self):
        return self.get_percent_max('policy_legislative_hearings')

    @property
    def total_percent_max(self):
        return self.get_percent_max('total_hearings')

    @property
    def investigative_oversight_percent_avg(self):
        return self.get_percent_avg('investigative_oversight_hearings')

    @property
    def policy_legislative_percent_avg(self):
        return self.get_percent_avg('policy_legislative_hearings')

    @property
    def total_percent_avg(self):
        return self.get_percent_avg('total_hearings')

    def get_percent_max(self, hearing_type):
        try:
            return int(round(getattr(self, hearing_type) \
                / getattr(self.committee, hearing_type + '_max') * 100))
        except ZeroDivisionError:
            return 0

    def get_percent_avg(self, hearing_type):
        try:
            return int(round(getattr(self, hearing_type) \
                / getattr(self.committee, hearing_type + '_avg') * 100))
        except ZeroDivisionError:
            return 0

    def __str__(self):
        return self.chp_grade


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


class ResetMixin(object):
    """Deletes and reloads this model in load_cms_content command."""
    reset_on_load = True


class StaticPage(ResetMixin, Page):
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

class LandingPage(ResetMixin, Page):
    body = RichTextField()

    # Editor configuration
    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    def get_context(self, request):
        context = super(LandingPage, self).get_context(request)
        context = CommitteeOrganization.objects.get_committee_context(context)
        return context


class DetailPage(ResetMixin, Page):
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

    def get_context(self, request):
        context = super(CommitteeDetailPage, self).get_context(request)
        context['latest_rating'] = context['page'].committee.latest_rating

        congresses = context['page'].committee.ratings_by_congress_asc \
            .values_list('congress_id', flat=True)
        context['congresses'] = [x for x in congresses]

        investigative_oversight_series = context['page'] \
            .committee.ratings_by_congress_asc.values_list(
            'investigative_oversight_hearings',
            flat=True
        )
        context['investigative_oversight_series'] = [x for x in \
            investigative_oversight_series]

        policy_legislative_series = context['page'].committee \
            .ratings_by_congress_asc.values_list(
            'policy_legislative_hearings',
            flat=True
        )
        context['policy_legislative_series'] = [x for x in \
            policy_legislative_series]

        total_series = context['page'].committee.ratings_by_congress_asc \
            .values_list(
            'total_hearings',
            flat=True
        )
        context['total_series'] = [x for x in total_series]

        return context

class HearingListPage(ResetMixin, Page):
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    def get_context(self, request):
        context = super(HearingListPage, self).get_context(request)
        context['categories'] = HearingCategoryType.objects.filter(
            name__in=settings.DISPLAY_CATEGORIES
        )
        return context


class CompareCurrentCommitteesPage(ResetMixin, Page):
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    def get_context(self, request):
        context = super(CompareCurrentCommitteesPage, self).get_context(request)
        context = CommitteeOrganization.objects.get_committee_context(context)
        return context


class CompareCommitteesOverCongressesPage(ResetMixin, Page):
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    def get_context(self, request):
        context = super(CompareCommitteesOverCongressesPage, self).get_context(request)
        context = CommitteeOrganization.objects.get_committee_context(context)
        return context

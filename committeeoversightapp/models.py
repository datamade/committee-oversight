import re
from datetime import date

from django.utils.text import slugify
from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.humanize.templatetags.humanize import ordinal
from django.db import models
from django.db.models import Max, Avg, Q
from django.db.models.fields import TextField, BooleanField
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError

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

from .model_utils import cap_100

class HearingEvent(Event):
    class Meta:
        proxy = True

    def get_absolute_url(self):
        return '/hearing/view/{}/'.format(self.id)

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

    def last_updated_all_committees(self):
        return max(
            [
                committee.last_updated
                for committee in self.permanent_committees()
            ]
        )

    def get_committee_context(self, context):
        context['committees'] = self.permanent_committees()
        context['house_committees'] = self.house_committees()
        context['senate_committees'] = self.senate_committees()
        context['last_updated'] = self.last_updated_all_committees()
        context['current_congress'] = Congress.objects.all().order_by("-id")[0]
        return context


class CommitteeOrganization(Organization):
    class Meta:
        proxy = True

    objects = CommitteeManager()

    @property
    def hearings(self):
        return HearingEvent.objects.all().filter(
            Q(participants__organization=self) |
            Q(participants__organization__parent=self)
        ).distinct()

    @property
    def last_updated(self):
        return self.hearings.exclude(
            hearingcategory__isnull=True
        ).aggregate(
            Max('updated_at')
        )['updated_at__max']

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
    def parent_proxy(self):
        return CommitteeOrganization.objects.get(id=self.parent.id)

    @property
    def display_name(self):
        try:
            display_name = CommitteeDetailPage.objects.get(
                committee=self.id
            ).display_name

            if display_name:
                return display_name
        except ObjectDoesNotExist:
            pass

        return self.name

    @property
    def short_name(self):
        if self.parent.name in settings.CHAMBERS:
            return re.sub(r'(House|Senate) Committee on ', '', self.display_name)
        return self.display_name

    @property
    def is_subcommittee(self):
        if self.parent.parent.name in settings.CHAMBERS:
            return True
        else:
            return False

    @property
    def is_permanent(self):
        if CommitteeOrganization.objects.permanent_committees().filter(id=self.id).exists():
            return True
        else:
            return False

    @property
    def get_linked_html(self):
        if self.is_subcommittee:
            if self.parent_proxy.is_permanent:
                return '<a href=\"{0}\">{1}</a>, {2}'.format(
                    self.parent_proxy.url,
                    self.parent,
                    self.name
                )
            else:
                return '{0}, {1}'.format(self.parent, self)
        else:
            if self.is_permanent:
                return '<a href="{0}">{1}</a>'.format(self.url, self)
            else:
                return self.display_name

    @property
    def get_linked_html_short(self):
        if self.is_subcommittee:
            if self.parent_proxy.is_permanent:
                return '<a href=\"{0}\">{1}</a>'.format(
                    self.parent_proxy.url,
                    self.parent
                )
            else:
                return self.parent
        else:
            if self.is_permanent:
                return '<a href="{0}">{1}</a>'.format(self.url, self)
            else:
                return self.display_name

    @property
    def chair(self):
        return CommitteeDetailPage.objects.get(committee=self.id).chair

    @property
    def hide_rating(self):
        return CommitteeDetailPage.objects.get(committee=self.id).hide_rating

    @property
    def ratings_by_congress_desc(self):
        return self.sort_congresses('-congress__id')

    @property
    def ratings_by_congress_asc(self):
        return self.sort_congresses('congress__id')

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

    def sort_congresses(self, sort_string):
        committeeratings = self.committeerating_set.all().order_by(sort_string)

        count = 1
        for rating in committeeratings:
            if rating.congress.footnote:
                rating.footnote_symbol = '*' * count
                count += 1
            else:
                rating.footnote_symbol = ''

        return committeeratings

    def __str__(self):
        return self.display_name


class Congress(models.Model):
    id = models.IntegerField(primary_key=True)
    start_date = models.DateField()
    end_date = models.DateField()
    inactive_days = models.IntegerField(
        default=settings.DEFAULT_CONGRESS_INACTIVE_DAYS,
        help_text="The default value here reflects the Lugar Center's determination "
        "that an average Congress does not hold hearings for about 2 months "
        "of its duration. Setting this value higher means that a Congress's "
        "scores will be calculated relative to a shorter length."
        )
    footnote = models.TextField(
        null=True,
        blank=True
    )

    panels = [
        FieldPanel('id'),
        FieldPanel('start_date'),
        FieldPanel('end_date'),
        FieldPanel('footnote'),
        FieldPanel('inactive_days')
    ]

    @property
    def length_in_days(self):
        return (self.end_date - self.start_date).days

    @property
    def normalizer(self):
        '''
        On average, we expect a Congress to be inactive for 62 days of its two year
        session. This accounts for Congresses that are inactive for longer; they
        should have a normalizer > 1.
        '''
        extra_inactive_days = self.inactive_days - settings.DEFAULT_CONGRESS_INACTIVE_DAYS
        normalizer =  self.length_in_days / (self.length_in_days - extra_inactive_days)

        return normalizer

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
        '''
        Returns the % of days passed of the current Congress compared
        to an average Congress length. This does not take atypical values
        for self.inactive_days into account, as inactive_days do not
        typically indicate a change in Congress's start and end dates
        '''
        days_passed = (date.today() - self.start_date).days

        percent_passed = round(
            days_passed / (
                self.length_in_days - settings.DEFAULT_CONGRESS_INACTIVE_DAYS
            ) * 100
        )

        return cap_100(percent_passed)

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
                / self.committee.max_chp_points * 100 \
                * self.congress.normalizer

            if not self.congress.is_current:
                return round(current_score)
            else:
                return round(current_score / self.congress.percent_passed \
                    * 100)

        except ZeroDivisionError:
            print("Divide by zero error on " + self.committee.display_name)
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
        ht = getattr(self, hearing_type)
        ht_max = getattr(self.committee, hearing_type + '_max')

        try:
            percent_max = round(ht / ht_max * 100 * self.congress.normalizer)
            return cap_100(percent_max)
        except ZeroDivisionError:
            return 0

    def get_percent_avg(self, hearing_type):
        ht = getattr(self, hearing_type)
        ht_avg = getattr(self.committee, hearing_type + '_avg')

        try:
            return round(ht / ht_avg * 100 * self.congress.normalizer)
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
        title = str(getattr(
            self, self.title_field
        ) or getattr(
            self, self.fallback_title_field)
        )

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
    title_field = 'display_name'
    fallback_title_field = 'committee'

    committee = models.ForeignKey(
        CommitteeOrganization,
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Select a committee for this page."
    )

    display_name = TextField(
        blank=True,
        null=True,
        help_text="Use this field to change the way a committee's name is "
        "displayed. If left empty, the name will not be modified.")

    chair = TextField(blank=True, null=True)

    hide_rating = BooleanField(default=False)

    content_panels = [
        FieldPanel('committee', widget=AutocompleteSelect(committee.remote_field, admin.site)),
        FieldPanel('body'),
        FieldPanel('chair'),
        FieldPanel('hide_rating'),
        FieldPanel('display_name')
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

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.core.validators import URLValidator, MinLengthValidator
from django.core.exceptions import ValidationError
import re


class SourceWebsite(models.Model):
    """
    Represents a website source for crawling vendor profiles.
    Stores configuration details for web scraping.
    """
    domain = models.CharField(
        max_length=255,
        unique=True,
        validators=[MinLengthValidator(3)],
        verbose_name=_("Domain Name"),
        help_text=_("The base domain of the source website (e.g., 'example.com')")
    )
    blog_path = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Blog Path"),
        help_text=_("Optional path to the blog section (e.g., '/blog')")
    )
    pagination_pattern = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Pagination Pattern"),
        help_text=_("Pattern for paginated URLs (e.g., '/page/{page}')")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether this source is actively crawled")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Creation Date"),
        help_text=_("When this source was added to the system")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated"),
        help_text=_("When this source was last modified")
    )

    class Meta:
        verbose_name = _("Source Website")
        verbose_name_plural = _("Source Websites")
        ordering = ['domain']
        indexes = [
            models.Index(fields=['domain'], name='idx_source_domain'),
            models.Index(fields=['is_active'], name='idx_source_active'),
        ]

    def __str__(self):
        return self.domain

    def clean(self):
        """Validate domain format."""
        if self.domain:
            if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', self.domain):
                raise ValidationError(_("Invalid domain format"))
        super().clean()


class Vendor(models.Model):
    """
    Represents a vendor profile with details about their services.
    Stores scraped or manually entered vendor information.
    """
    title = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(2)],
        verbose_name=_("Vendor Title"),
        help_text=_("The name of the vendor or service provider")
    )
    description = models.TextField(
        verbose_name=_("Service Description"),
        help_text=_("Detailed description of the services offered")
    )
    price = models.CharField(
        max_length=100,
        verbose_name=_("Service Price"),
        help_text=_("Pricing information (e.g., 'Starting at $1,500', 'Packages available')")
    )
    image_link = models.URLField(
        max_length=512,
        validators=[URLValidator()],
        verbose_name=_("Vendor Image URL"),
        help_text=_("URL of the vendor's featured image or logo")
    )
    article_link = models.URLField(
        max_length=512,
        unique=True,
        validators=[URLValidator()],
        verbose_name=_("Vendor Profile URL"),
        help_text=_("Full URL to the vendor's profile page on the source website")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Creation Date"),
        help_text=_("Date when this record was first created in the system")
    )

    class Meta:
        verbose_name = _("Vendor Profile")
        verbose_name_plural = _("Vendor Profiles")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title'], name='idx_vendor_title'),
            models.Index(fields=['created_at'], name='idx_vendor_created'),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        """Validate price format and URLs."""
        if self.price and not re.match(r'^[\w\s$,.+-]+$', self.price):
            raise ValidationError(_("Price contains invalid characters"))
        super().clean()

    def get_short_description(self, length=100):
        """Return a truncated description for previews."""
        return (self.description[:length] + '...') if len(self.description) > length else self.description


class CrawledPost(models.Model):
    """
    Stores raw data from crawled web pages before processing into Vendor profiles.
    """
    source = models.ForeignKey(
        SourceWebsite,
        on_delete=models.CASCADE,
        related_name='crawled_posts',
        verbose_name=_("Source Website"),
        help_text=_("The source website this post was crawled from")
    )
    url = models.URLField(
        max_length=1000,
        unique=True,
        validators=[URLValidator()],
        verbose_name=_("Post URL"),
        help_text=_("The URL of the crawled post")
    )
    title = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Post Title"),
        help_text=_("The title of the crawled post")
    )
    content = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Post Content"),
        help_text=_("The main content of the crawled post")
    )
    raw_html = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Raw HTML"),
        help_text=_("The raw HTML content of the crawled page")
    )
    metadata = JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
        help_text=_("Additional metadata extracted from the post")
    )
    is_processed = models.BooleanField(
        default=False,
        verbose_name=_("Is Processed"),
        help_text=_("Whether this post has been processed into a Vendor profile")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Creation Date"),
        help_text=_("When this post was crawled")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated"),
        help_text=_("When this post was last modified")
    )

    class Meta:
        verbose_name = _("Crawled Post")
        verbose_name_plural = _("Crawled Posts")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source', 'is_processed'], name='idx_post_source_processed'),
            models.Index(fields=['url'], name='idx_post_url'),
        ]

    def __str__(self):
        return self.title or self.url

    def clean(self):
        """Validate URL and metadata."""
        if isinstance(self.metadata, dict):
            if len(str(self.metadata)) > 10000:
                raise ValidationError(_("Metadata is too large"))
        else:
            raise ValidationError(_("Metadata must be a dictionary"))
        super().clean()


class CrawlLog(models.Model):
    """
    Logs crawling activities for monitoring and debugging.
    """
    source = models.ForeignKey(
        SourceWebsite,
        on_delete=models.CASCADE,
        related_name='crawl_logs',
        verbose_name=_("Source Website"),
        help_text=_("The source website this crawl log pertains to")
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ('SUCCESS', _("Success")),
            ('FAILURE', _("Failure")),
            ('PARTIAL', _("Partial Success")),
        ],
        verbose_name=_("Status"),
        help_text=_("The status of the crawl operation")
    )
    message = models.TextField(
        verbose_name=_("Message"),
        help_text=_("Details about the crawl operation (e.g., errors, summary)")
    )
    posts_found = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Posts Found"),
        help_text=_("Number of posts found during this crawl")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Creation Date"),
        help_text=_("When this crawl log was created")
    )

    class Meta:
        verbose_name = _("Crawl Log")
        verbose_name_plural = _("Crawl Logs")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source', 'status'], name='idx_log_source_status'),
            models.Index(fields=['created_at'], name='idx_log_created'),
        ]

    def __str__(self):
        return f"{self.source.domain} - {self.status}"

    def clean(self):
        """Validate status and posts_found."""
        if self.posts_found < 0:
            raise ValidationError(_("Posts found cannot be negative"))
        if self.status not in dict(self._meta.get_field('status').choices):
            raise ValidationError(_("Invalid status value"))
        super().clean()

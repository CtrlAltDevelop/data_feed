from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField


class Vendor(models.Model):
    title = models.CharField(
        max_length=255,
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
        verbose_name=_("Vendor Image URL"),
        help_text=_("URL of the vendor's featured image or logo")
    )

    article_link = models.URLField(
        max_length=512,
        unique=True,
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

    def __str__(self):
        return self.title

class SourceWebsite(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    blog_path = models.CharField(max_length=255, blank=True, null=True)
    pagination_pattern = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.domain

class CrawledPost(models.Model):
    source = models.ForeignKey(SourceWebsite, on_delete=models.CASCADE)
    url = models.URLField(max_length=1000, unique=True)
    title = models.CharField(max_length=500, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    raw_html = models.TextField(blank=True, null=True)
    metadata = JSONField(default=dict, blank=True)
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title or self.url

class CrawlLog(models.Model):
    source = models.ForeignKey(SourceWebsite, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    message = models.TextField()
    posts_found = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.source.domain} - {self.status}"
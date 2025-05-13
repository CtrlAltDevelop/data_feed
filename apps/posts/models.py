from django.db import models
from django.utils.translation import gettext_lazy as _


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

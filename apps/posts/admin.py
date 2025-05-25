from django.contrib import admin
from django.utils.html import format_html
from .models import Vendor,SourceWebsite,CrawledPost,CrawlLog

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'image_preview', 'article_link', 'created_at')
    list_filter = ('price', 'created_at')
    search_fields = ('title', 'description')
    list_per_page = 20
    exclude = ('created_at',)  # Hide from edit form since it's auto-generated

    def image_preview(self, obj):
        if obj.image_link:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image_link
            )
        return "-"
    image_preview.short_description = 'Image'

    def article_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">View Article</a>',
            obj.article_link
        )
    article_link.short_description = 'Link'

    readonly_fields = ('article_link', 'created_at')  # Make these fields read-only


@admin.register(SourceWebsite)
class SourceWebsiteAdmin(admin.ModelAdmin):
    list_display = ('domain', 'is_active', 'created_at')
    search_fields = ('domain',)

@admin.register(CrawledPost)
class CrawledPostAdmin(admin.ModelAdmin):
    list_display = ('url', 'source', 'is_processed', 'created_at')
    search_fields = ('url', 'title')
    list_filter = ('is_processed',)

@admin.register(CrawlLog)
class CrawlLogAdmin(admin.ModelAdmin):
    list_display = ('source', 'status', 'posts_found', 'created_at')
    list_filter = ('status',)
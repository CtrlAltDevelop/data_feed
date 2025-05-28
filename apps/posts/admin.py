from .models import SourceWebsite, Vendor, CrawledPost, CrawlLog
from django.utils.translation import gettext_lazy as _
from ckeditor.widgets import CKEditorWidget
from django import forms
from django.contrib import admin


class SourceWebsiteAdminForm(forms.ModelForm):
    class Meta:
        model = SourceWebsite
        fields = '__all__'

    def clean_domain(self):
        domain = self.cleaned_data['domain']
        if SourceWebsite.objects.filter(domain=domain).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("This domain is already registered."))
        return domain


@admin.register(SourceWebsite)
class SourceWebsiteAdmin(admin.ModelAdmin):
    form = SourceWebsiteAdminForm
    list_display = ('domain', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('domain', 'blog_path', 'pagination_pattern')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('domain', 'blog_path', 'pagination_pattern', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 25

    def has_import_permission(self, request):
        return request.user.is_superuser


class VendorAdminForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = '__all__'

    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    form = VendorAdminForm
    list_display = ('title', 'price', 'created_at', 'get_short_description')
    list_filter = ('created_at',)
    search_fields = ('title', 'description', 'price', 'article_link')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'price', 'image_link', 'article_link')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


class CrawledPostAdminForm(forms.ModelForm):
    class Meta:
        model = CrawledPost
        fields = '__all__'
        widgets = {
            'raw_html': CKEditorWidget(config_name='default'),
            'content': forms.Textarea(attrs={'rows': 5}),
        }


@admin.register(CrawledPost)
class CrawledPostAdmin(admin.ModelAdmin):
    form = CrawledPostAdminForm
    list_display = ('title', 'source', 'is_processed', 'created_at')
    list_filter = ('source', 'is_processed', 'created_at')
    search_fields = ('title', 'url', 'content')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('source', 'url', 'title', 'content', 'metadata', 'is_processed')
        }),
        (_('HTML'), {
            'fields': ('raw_html', ),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('source')


@admin.register(CrawlLog)
class CrawlLogAdmin(admin.ModelAdmin):
    list_display = ('source', 'status', 'posts_found', 'created_at')
    list_filter = ('source', 'status', 'created_at')
    search_fields = ('source__domain', 'message', 'status')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('source', 'status', 'message', 'posts_found')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('source')

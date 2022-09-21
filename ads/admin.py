from django.contrib import admin
from ads.models import ContactUs, ReportAd, ScrapedAd, AdCategory

# Register your models here.
class ContactUsAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified',)
    ordering = ('-created',)

class ReportAdAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified',)
    ordering = ('-created',)

class ScrapedAdAdmin(admin.ModelAdmin):
    readonly_fields = ('last_posted',)
    ordering = ('-last_posted',)

class AdCategoryAdmin(admin.ModelAdmin):
    ordering = ('-id',)
    
admin.site.register(ContactUs, ContactUsAdmin)
admin.site.register(ReportAd, ReportAdAdmin)
admin.site.register(ScrapedAd, ScrapedAdAdmin)
admin.site.register(AdCategory, AdCategoryAdmin)

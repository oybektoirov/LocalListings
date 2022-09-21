from django.contrib import admin
from .models import CommunityAd

class CommunityAdAdmin(admin.ModelAdmin):
	readonly_fields = ('created', 'modified',)
	
admin.site.register(CommunityAd, CommunityAdAdmin)


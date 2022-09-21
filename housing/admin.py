from django.contrib import admin
from .models import HousingAd

class HousingAdAdmin(admin.ModelAdmin):
	readonly_fields = ('created', 'modified',)
	
admin.site.register(HousingAd, HousingAdAdmin)


from django.contrib import admin
from .models import ServicesAd

class ServicesAdAdmin(admin.ModelAdmin):
	readonly_fields = ('created', 'modified',)
	
admin.site.register(ServicesAd, ServicesAdAdmin)


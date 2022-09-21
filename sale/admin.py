from django.contrib import admin
from .models import SaleAd

class SaleAdAdmin(admin.ModelAdmin):
	readonly_fields = ('created', 'modified',)
	
admin.site.register(SaleAd, SaleAdAdmin)


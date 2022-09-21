from __future__ import unicode_literals

from django.db import models
from django.conf import settings

class City(models.Model):
    name = models.CharField(max_length=60)
    short_name = models.CharField(max_length=60, db_index=True)
    short_state = models.CharField(max_length=60, db_index=True)
    long_state = models.CharField(max_length=60)
    country = models.CharField(max_length=60)
    region = models.CharField(max_length=40, db_index=True)
    timezone = models.CharField(max_length=30)

    def __unicode__(self):
       return self.name + ', ' + self.short_state

    def get_city_url(self):
        if 'https' in settings.SITE_URL:
            return 'https://%s.%s' % (self.short_name, settings.DOMAIN)
        else:
            return 'http://%s.%s' % (self.short_name, settings.DOMAIN)




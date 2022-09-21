from __future__ import unicode_literals
import uuid
from django.db import models
from account.models import MainUser
from geocity.models import City
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import python_2_unicode_compatible

class BasicInfo(models.Model):
    creator = models.ForeignKey(MainUser, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class ContactUs(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    email = models.EmailField(
        verbose_name='email address', 
        max_length=60, 
    )
    message = models.TextField(blank=False)

    def __str__(self):
        return '%s, %s' % (self.email, self.message[:15])

class ReportAd(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    flag_message = models.CharField(
        max_length=30, default='', 
        blank=False, choices=settings.REPORTAD_CHOICES)
    content_type = models.ForeignKey(ContentType)
    object_id = models.CharField(max_length=50)
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return '%s, %s' % (self.id, self.flag_message)


class AdCategory(models.Model):
    slug = models.SlugField()
    section = models.CharField(max_length=15, blank=False, db_index=True)
    pretty_name = models.CharField(max_length=60, blank=False)

    def __str__(self):
        return self.pretty_name


class AdUpgradeOrder(models.Model):
    order_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
    )
    order_date = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    payment_method = models.CharField(
        max_length=10,
        blank=True,
        default='',
        choices=settings.PAYMENT_METHOD_CHOICES,
    )
    times_to_move = models.CharField(
        max_length=2,
        default='0',
    )
    sponsored_weeks = models.CharField(
        max_length=2,
        default='0',
    )
    freedom_plan = models.BooleanField(default=False)
    amount = models.IntegerField()
    market_quantity = models.PositiveSmallIntegerField(default=1)
    stripe_charge_id = models.CharField(max_length=30, blank=True, default='')

    class Meta:
        abstract = True


class Ad(BasicInfo):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
    )
    edit_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True, 
    )
    posted = models.DateTimeField(
        default=timezone.now, 
        editable=True, 
        blank=True,
    )
    status = models.CharField(
        max_length=15, 
        default='', 
        choices=settings.STATUS_CHOICES,
        db_index=True,
    )
    category = models.ForeignKey(AdCategory, blank=False)
    category_slug = models.SlugField()
    title = models.CharField(max_length=170, blank=False)
    body = models.TextField(blank=False)
    email = models.EmailField(
        verbose_name='email address', 
        max_length=60, 
        blank=True,
    )
    images = models.CharField(max_length=600, blank=True, default='')
    city = models.ForeignKey(City, blank=False, 
        related_name='%(app_label)s_%(class)s_city_related',
    )
    city_short_name = models.CharField(max_length=60)
    agree_to_terms = models.BooleanField(default=True)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class ScrapedAd(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
    )
    last_posted = models.DateTimeField(
        default=timezone.now, 
        editable=True, 
        blank=True,
    )
    title = models.CharField(max_length=200, blank=False)
    body = models.TextField(blank=False)
    post_id = models.CharField(max_length=15, blank=False, db_index=True)
    images = models.CharField(max_length=1200, blank=True, default='')
    age = models.PositiveSmallIntegerField(default=21)
    city = models.ForeignKey(City, blank=False, 
        related_name='%(app_label)s_%(class)s_city_related',
    )
    city_short_name = models.CharField(max_length=60)
    link = models.URLField(max_length=500, blank=True)
    location = models.CharField(max_length=120, blank=True, default='')
    phone = models.CharField(max_length=12, blank=True, default='')

    def __str__(self):
        return '%s, %s' % (self.id, self.title[:15])

    def image_list_large(self):
        img_list = []
        if self.images:
            for image in self.images.split(','):
                img_list.append(img)
        return img_list

    def image_list_medium(self):
        img_list = []
        if self.images:
            for image in self.images.split(','):
                img = image.replace('large', 'medium')
                img_list.append(img)
        return img_list

    def image_list_small(self):
        img_list = []
        if self.images:
            for image in self.images.split(','):
                img = image.replace('large', 'small')
                img_list.append(img)
        return img_list

    def get_images(self):
        img_list = []
        if self.images:
            for image in self.images.split(','):
                data = {}
                data['small'] = image.replace('large', 'small')
                data['medium'] = image.replace('large', 'medium')
                data['large'] = image
                img_list.append(data)
        return img_list

    def get_ad_url(self):
        return self.city.get_city_url() + '/escorts/ext/%s' % self.id

    




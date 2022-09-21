from __future__ import unicode_literals
from django.db import models
from ads.models import Ad
from geocity.models import City
from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible
from django.db.models import signals
import utils
import boto3

domain = settings.DOMAIN
img_bucket = settings.S3_IMG_BUCKET

@python_2_unicode_compatible
class CommunityAd(Ad):
    pass

    def __str__(self):
        return '{}, {}'.format(self.id, self.title[:15])

    def image_list_large(self):
    	img_list = []
    	if self.images:
    		for image in self.images.split(','):
    			img = 'https://s3.amazonaws.com/{}/large/{}'.format(img_bucket, image)
    			img_list.append(img)
    	return img_list

    def image_list_medium(self):
    	img_list = []
    	if self.images:
    		for image in self.images.split(','):
    			img = 'https://s3.amazonaws.com/{}/medium/{}'.format(img_bucket, image)
    			img_list.append(img)
    	return img_list

    def image_list_small(self):
    	img_list = []
    	if self.images:
    		for image in self.images.split(','):
    			img = 'https://s3.amazonaws.com/{}/small/{}'.format(img_bucket, image)
    			img_list.append(img)
    	return img_list

    def get_images(self):
        img_list = []
        if self.images:
            for image in self.images.split(','):
                data = {}
                data['small'] = 'https://s3.amazonaws.com/{}/small/{}'.format(img_bucket, image)
                data['medium'] = 'https://s3.amazonaws.com/{}/medium/{}'.format(img_bucket, image)
                data['large'] = 'https://s3.amazonaws.com/{}/large/{}'.format(img_bucket, image)
                img_list.append(data)
        return img_list

    def get_ad_url(self):
    	return self.city.get_city_url() + '/{}/{}/{}'.format(
            self.category.section, 
    		self.category.slug,
    		self.id,
    	)

 
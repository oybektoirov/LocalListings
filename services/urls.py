from django.conf.urls import url
from . import views


app_name = 'services'

urlpatterns = [
    url(r'^(?P<category_slug>[-\w]+)/(?P<ad_id>[-\w]+)', views.ad_detail, name='ad_detail'),
    url(r'^(?P<category_slug>[-\w]+)', views.listings, name='listings'),
]
from django.conf.urls import url
from . import views


app_name = 'ads'

urlpatterns = [
	url(r'^post-ad/$', views.post_ad, name='post-ad'),
]
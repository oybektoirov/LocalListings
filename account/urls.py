from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^$', views.account, name='account'),
    url(r'^login/', views.login, name='login'),
    url(r'^logout/', auth_views.logout, {'next_page': '/'}, name='logout'),
    url(r'^create/', views.create, name='create'),
    url(r'^password-reset-request/', views.password_reset_request, name='password_reset_request'),
    url(r'^password-reset/(?P<token>[-\w]+)', views.password_reset, name='password_reset'),
    url(r'^change-password/', views.change_password, name='change_password'),
    url(r'^buy-credits/', views.buy_credits, name='buy_credits'),
]
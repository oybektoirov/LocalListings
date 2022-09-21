from django.shortcuts import render, redirect
from django.conf import settings
from models import HousingAd
from geocity.models import City
from ads.models import AdCategory
from django.core.validators import validate_email
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from itertools import chain
from account.models import MainUser
from django.db import transaction
import utils
import pytz
import stripe
import requests
import datetime
import uuid

site_url = settings.SITE_URL
ad_sections = settings.AD_SECTIONS
img_bucket = settings.S3_IMG_BUCKET
cookie_city_id = settings.COOKIE_CITY_ID
domain = settings.DOMAIN

def post_ad(request, category):
    addcookie = False
    cookie_cityid = request.COOKIES.get(cookie_city_id, '')
    regionid = request.GET.get('region', '').replace('/', '').strip()
    try:
        if not cookie_cityid:
            city = City.objects.get(id=regionid)
            addcookie = True
        elif regionid and cookie_cityid != regionid:
            city = City.objects.get(id=regionid)
            addcookie = True
        else:
            city = City.objects.get(id=cookie_cityid)
    except:
        return redirect(site_url + '/post-ad/')
    timezone.activate(pytz.timezone(city.timezone))
    
    try:
        cat = AdCategory.objects.get(id=category)
    except:
        return redirect(site_url + '/post-ad/') 

    edit_token = request.GET.get('token', '').replace('/', '').strip()
    if edit_token:
        try:
            ad = HousingAd.objects.get(edit_token=edit_token)
            if ad.status == 'removedbyuser':
                return redirect(site_url + '/post-ad/', permanent=True)
            nearby_cities = City.objects.filter(short_state=ad.city.short_state)
            context = {}
            context['ad'] = ad
            context['category'] = cat
            if ad.images:
                images = ad.images.split(',')
                context['images'] = images
            context['city'] = ad.city
            context['city_url'] = ad.city.get_city_url()
            context['nearby_cities'] = nearby_cities
            context['S3_IMG_BUCKET'] = img_bucket
            context['bad_words_list'] = settings.FILTER_WORDS_HEX
            context['edit'] = True
            response = render(request, 'housing/writead.html', context)
            if addcookie:
                return utils.render_with_cookie(response, ad.city)
            else:
                return response
        except:
            pass      

    if request.method == 'POST':
        saveonly = request.POST.get('saveonly', '')
        delete = request.POST.get('delete', '')
        if delete == 'true':
            try:
                ad = HousingAd.objects.get(id=request.POST['adid'])
                ad.status = 'removedbyuser'
                ad.save()
                return redirect(site_url)
            except:
                return redirect(site_url)
        #when a user requests to edit ad
        if request.POST['nextstep'] == '1':
            nearby_cities = City.objects.filter(short_state=city.short_state)
            ad = HousingAd.objects.get(id=request.POST['adid'])
            context = {}
            context['ad'] = ad
            context['category'] = cat
            if ad.images:
                images = ad.images.split(',')
                context['images'] = images
            context['city'] = city
            context['city_url'] = city.get_city_url()
            context['nearby_cities'] = nearby_cities
            context['S3_IMG_BUCKET'] = img_bucket
            context['bad_words_list'] = settings.FILTER_WORDS_HEX
            return render(request, 'housing/writead.html', context)

        #load done page
        if request.POST['nextstep'] == '3':
            recaptcha = request.POST.get('g-recaptcha-response', '')
            if recaptcha:
                payload = {}
                payload['response'] = recaptcha
                payload['secret'] = settings.RECAPTCHA_SECRET_KEY
                r = requests.post(settings.RECAPTCHA_VERIFY_URL, data=payload)
                if not r.json()['success']:
                    return redirect(site_url + '/post-ad/')
            else:
                return redirect(site_url + '/post-ad/')
            context = {}
            ad = HousingAd.objects.get(id=request.POST['adid'])
            ad.status = 'live'
            ad.save()
            context['ad'] = ad
            context['category'] = cat
            context['city'] = city
            context['city_url'] = city.get_city_url()
            utils.send_newad_email(ad, cat)
            return render(request, 'housing/donead.html', context)


        title = request.POST['title']
        #validation is done on client side as well
        if not title:
            raise ValueError('Ad title is empty')

        body = request.POST['body']
        #validation is done on client side as well
        if not body:
            raise ValueError('Ad body is empty')

        for word in settings.FILTER_WORDS_HEX:
            if word.decode('hex') in body.lower():
                return redirect(site_url + '/post-ad/')

        images = request.POST.get('allimages', '')
        agree_to_terms = request.POST.get('terms', '')
        if agree_to_terms != 'on':
            return redirect(site_url + '/post-ad/')

        #preparing for preview ad
        adid = request.POST.get('adid', '')
        if adid:
            ad = HousingAd.objects.get(id=adid)
        else:
            ad = HousingAd(status='pending') #pending
            ad.category = cat
            ad.city = city
            ad.category_slug = cat.slug
            ad.city = city
            ad.city_short_name = city.short_name
        ad.title = title
        ad.body = body
        if request.user.is_authenticated:
            ad.creator = request.user
            ad.email = request.user.email
        else:
            email = request.POST.get('email', '')
            validate_email(email)
            ad.email = email

        if images:
            ad.images = images
        elif ad.images:
            ad.images = ''

        ad.save()
        if saveonly == 'true':
            return redirect(ad.get_ad_url())
        
        context = {}
        context['ad'] = ad
        context['city'] = city
        context['city_url'] = city.get_city_url()
        if images:
            context['images'] = ad.image_list_medium()
        context['category'] = cat
        context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
        return render(request, 'housing/previewad.html', context)

    nearby_cities = City.objects.filter(short_state=city.short_state)
    context = {}
    context['city'] = city
    context['city_url'] = city.get_city_url()
    context['nearby_cities'] = nearby_cities
    context['category'] = cat
    context['S3_IMG_BUCKET'] = img_bucket
    context['bad_words_list'] = settings.FILTER_WORDS_HEX
    response = render(request, 'housing/writead.html', context)
    if addcookie:
        return utils.render_with_cookie(response, city)
    else:
        return response

def listings(request, category_slug):
    cookie_cityid = request.COOKIES.get(cookie_city_id, '')
    subdomain = utils.get_subdomain(request)
    addcookie = False
    if cookie_cityid:
        try:
            city = City.objects.get(id=cookie_cityid)
            if city.short_name != subdomain:
                addcookie = True
                city = City.objects.get(short_name=subdomain)
        except:
            if subdomain:
                addcookie = True
                city = City.objects.get(short_name=subdomain)
            else:
                return redirect(site_url + '/all-cities/')
    else:
        addcookie = True
        city = City.objects.get(short_name=subdomain)

    timezone.activate(pytz.timezone(city.timezone))
    
    nearby_cities = City.objects.filter(short_state=city.short_state)

    try:
        category = AdCategory.objects.get(slug=category_slug)
    except:
        return redirect(site_url)

    categories = AdCategory.objects.filter(section=category.section)

    page = request.GET.get('page', 1)
    top_ads = HousingAd.objects.filter(
        category=category,
        city=city,
        status='live',
    ).order_by('-posted')
    first_more_ad_id = ''

    result_list = list(chain(top_ads))
    paginator = Paginator(result_list, 100)
    try:
        all_ads = paginator.page(int(page))
    except PageNotAnInteger:
        all_ads = paginator.page(1)
    except EmptyPage:
        all_ads = paginator.page(paginator.num_pages)

    context = {}
    context['city'] = city
    context['city_url'] = city.get_city_url()
    context['nearby_cities'] = nearby_cities
    context['categories'] = categories
    context['category'] = category
    context['all_ads'] = all_ads
    context['first_more_ad_id'] = first_more_ad_id

    response = render(request, 'housing/listings.html', context)
    if addcookie:
        return utils.render_with_cookie(response, city)
    else:
        return response

def ad_detail(request, category_slug, ad_id):
    cookie_cityid = request.COOKIES.get(cookie_city_id, '')
    subdomain = utils.get_subdomain(request)
    try:
        ad = HousingAd.objects.get(id=ad_id)
    except:
        if subdomain:
            city = City.objects.get(short_name=subdomain)
            return redirect('{}/housing/{}'.format(city.get_city_url(), category_slug))
        else:
            return redirect(site_url)

    category = AdCategory.objects.get(slug=category_slug)
    categories = AdCategory.objects.filter(section=category.section)
    addcookie = False
    if cookie_cityid:
        try:
            city = City.objects.get(id=cookie_cityid)
            if city.id != ad.city_id:
                addcookie = True
                city = ad.city
        except:
            addcookie = True
            city = ad.city
    else:
        addcookie = True
        city = ad.city

    nearby_cities = City.objects.filter(short_state=city.short_state)
    timezone.activate(pytz.timezone(city.timezone))

    if ad.status != 'live':
        if ad.creator:
            if not ad.creator.pk == request.user.pk:
                return redirect('%s/housing/%s' % (city.get_city_url(), category_slug))
        else:
            return redirect('%s/housing/%s' % (city.get_city_url(), category_slug))

    context = {}
    context['ad'] = ad
    context['city'] = city
    context['city_url'] = city.get_city_url()
    context['nearby_cities'] = nearby_cities
    context['categories'] = categories
    context['category'] = category
    response = render(request, 'housing/ad_detail.html', context)
    if addcookie:
        return utils.render_with_cookie(response, city)
    else:
        return response



from django.shortcuts import render, redirect
from django.conf import settings
from geocity.models import City
from ads.models import AdCategory, ReportAd, ScrapedAd
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from itertools import chain
from leisure.models import LeisureAd
from community.models import CommunityAd
from housing.models import HousingAd
from jobs.models import JobsAd
from sale.models import SaleAd
from services.models import ServicesAd
from django.db.models import Q
from ads.models import ContactUs
from django.core.validators import validate_email
from django.db import transaction
from raven.contrib.django.raven_compat.models import client as raven_client
import utils
import pytz
import datetime
import operator
import requests

cookie_cityid_name = settings.COOKIE_CITY_ID
site_url = settings.SITE_URL

def post_ad(request):
    sections = []
    for section in settings.AD_SECTIONS:
        categories = AdCategory.objects.filter(section=section)
        sections.append([section, categories])

    cookie_cityid = request.COOKIES.get(cookie_cityid_name, '')
    if not cookie_cityid:
        context = {}
        cities = City.objects.all().order_by('short_name')
        context['sections'] = sections
        context['cities'] = cities
        context['catUseRegions'] = True
        return render(request, 'ads/postad.html', context)

    try:
        city = City.objects.get(id=cookie_cityid)
        context = {}
        context['sections'] = sections
        return render(request, 'ads/postad.html', context)
    except Exception:
        raven_client.captureException()
        return redirect(site_url + '/all-cities/')

def index(request):
    sections = []
    for section in settings.AD_SECTIONS:
        categories = AdCategory.objects.filter(section=section)
        sections.append([section, categories])

    cookie_cityid = request.COOKIES.get(cookie_cityid_name, '')
    subdomain = utils.get_subdomain(request)
    if not cookie_cityid:
        try:
            city = City.objects.get(short_name=subdomain)
            nearby_cities = City.objects.filter(short_state=city.short_state)
            context = {}
            context['city'] = city
            context['city_url'] = city.get_city_url()
            context['sections'] = sections
            context['nearby_cities'] = nearby_cities
            response = render(request, 'ads/index.html', context)
            return utils.render_with_cookie(response, city)
        except:
            return redirect(site_url + '/all-cities/')

    try:
        city = City.objects.get(id=cookie_cityid)
        if city.short_name != subdomain:
            if not subdomain:
                return redirect(city.get_city_url())

            try:
                city = City.objects.get(short_name=subdomain)
                nearby_cities = City.objects.filter(short_state=city.short_state)
                context = {}
                context['city'] = city
                context['city_url'] = city.get_city_url()
                context['sections'] = sections
                context['nearby_cities'] = nearby_cities
                response = render(request, 'ads/index.html', context)
                return utils.render_with_cookie(response, city)
            except Exception:
                raven_client.captureException()
                return redirect(site_url + '/all-cities/')

        nearby_cities = City.objects.filter(short_state=city.short_state)
        context = {}
        context['city'] = city
        context['city_url'] = city.get_city_url()
        context['sections'] = sections
        context['nearby_cities'] = nearby_cities
        return render(request, 'ads/index.html', context)
    except:
        try:
            city = City.objects.get(short_name=subdomain)
        except Exception:
            raven_client.captureException()
            return redirect(site_url + '/all-cities/')
        nearby_cities = City.objects.filter(short_state=city.short_state)
        context = {}
        context['city'] = city
        context['city_url'] = city.get_city_url()
        context['sections'] = sections
        context['nearby_cities'] = nearby_cities
        response = render(request, 'ads/index.html', context)
        return utils.render_with_cookie(response, city)

def all_cities(request):
    europe = City.objects.filter(region='Europe').order_by('country')
    us = City.objects.filter(region='United States').order_by('long_state')
    canada = City.objects.filter(region='Canada').order_by('long_state')
    apm = City.objects.filter(region='Asia, Pacific, and Middle East').order_by('country')
    australia = City.objects.filter(region='Australia and Oceania').order_by('country')
    latin = City.objects.filter(region='Latin America and Caribbean').order_by('country')
    africa = City.objects.filter(region='Africa').order_by('country')
    context = {}
    context['europe'] = europe
    context['us'] = us
    context['canada'] = canada
    context['apm'] = apm
    context['australia'] = australia
    context['latin'] = latin
    context['africa'] = africa
    return render(request, 'ads/all_cities.html', context)

def search(request):
    cookie_cityid = request.COOKIES.get(cookie_cityid_name, '')

    if not cookie_cityid:
        return redirect(site_url + '/all-cities/')

    city = City.objects.get(id=cookie_cityid)
    timezone.activate(pytz.timezone(city.timezone))
    nearby_cities = City.objects.filter(short_state=city.short_state)

    categoryid = request.GET.get('categoryid', '')
    if not categoryid:
        return redirect(site_url)
    keyword = request.GET.get('keyword', '')

    category = AdCategory.objects.get(id=categoryid)
    categories = AdCategory.objects.filter(section=category.section)

    page = request.GET.get('page', 1)
    all_ads = {}
    sponsored_ads = {}
    first_more_ad_id = ''
    if category.section == 'leisure':
        top_ads = LeisureAd.objects.filter(Q(
            category=category,
            city=city,
            status='live',
            top=True,
            title__icontains=keyword,
        )|Q(
            category=category,
            city=city,
            status='live',
            top=True,
            body__icontains=keyword,
        )).order_by('-last_posted')
        additional_ads = LeisureAd.objects.filter(Q(
            category=category,
            city=city,
            status='live',
            sponsored=False,
            top=False,
            title__icontains=keyword,
        )|Q(
            category=category,
            city=city,
            status='live',
            sponsored=False,
            top=False,
            body__icontains=keyword,
        )).order_by('-last_posted')
        if category.slug == 'escorts':
            scraped_ads = ScrapedAd.objects.filter(Q(
                city=city,
                title__icontains=keyword,
            )|Q(
                city=city,
                body__icontains=keyword,
            )).order_by('-last_posted')
        else:
            scraped_ads = []
        if additional_ads:
            first_more_ad_id = additional_ads[0].id
            
        result_list = list(chain(top_ads, additional_ads, scraped_ads))
        paginator = Paginator(result_list, 100)
        try:
            all_ads = paginator.page(int(page))
        except PageNotAnInteger:
            all_ads = paginator.page(1)
        except EmptyPage:
            all_ads = paginator.page(paginator.num_pages)

        sponsored_ads = LeisureAd.objects.filter(Q(
            category=category,
            city=city,
            status='live',
            sponsored=True,
            title__icontains=keyword,
        )|Q(
            category=category,
            city=city,
            status='live',
            sponsored=True,
            body__icontains=keyword,
        )).order_by('-last_posted')

    elif category.section == 'community':
        top_ads = CommunityAd.objects.filter(Q(
            category=category,
            city=city,
            status='live',
            title__icontains=keyword,
        )|Q(
            category=category,
            city=city,
            status='live',
            body__icontains=keyword,
        )).order_by('-posted')
            
        result_list = list(chain(top_ads))
        paginator = Paginator(result_list, 100)
        try:
            all_ads = paginator.page(int(page))
        except PageNotAnInteger:
            all_ads = paginator.page(1)
        except EmptyPage:
            all_ads = paginator.page(paginator.num_pages)

    elif category.section == 'housing':
        top_ads = HousingAd.objects.filter(Q(
            category=category,
            city=city,
            status='live',
            title__icontains=keyword,
        )|Q(
            category=category,
            city=city,
            status='live',
            body__icontains=keyword,
        )).order_by('-posted')
            
        result_list = list(chain(top_ads))
        paginator = Paginator(result_list, 100)
        try:
            all_ads = paginator.page(int(page))
        except PageNotAnInteger:
            all_ads = paginator.page(1)
        except EmptyPage:
            all_ads = paginator.page(paginator.num_pages)

    elif category.section == 'jobs':
        top_ads = JobsAd.objects.filter(Q(
            category=category,
            city=city,
            status='live',
            title__icontains=keyword,
        )|Q(
            category=category,
            city=city,
            status='live',
            body__icontains=keyword,
        )).order_by('-posted')
            
        result_list = list(chain(top_ads))
        paginator = Paginator(result_list, 100)
        try:
            all_ads = paginator.page(int(page))
        except PageNotAnInteger:
            all_ads = paginator.page(1)
        except EmptyPage:
            all_ads = paginator.page(paginator.num_pages)

    elif category.section == 'sale':
        top_ads = SaleAd.objects.filter(Q(
            category=category,
            city=city,
            status='live',
            title__icontains=keyword,
        )|Q(
            category=category,
            city=city,
            status='live',
            body__icontains=keyword,
        )).order_by('-posted')

        result_list = list(chain(top_ads))
        paginator = Paginator(result_list, 100)
        try:
            all_ads = paginator.page(int(page))
        except PageNotAnInteger:
            all_ads = paginator.page(1)
        except EmptyPage:
            all_ads = paginator.page(paginator.num_pages)

    elif category.section == 'services':
        top_ads = ServicesAd.objects.filter(Q(
            category=category,
            city=city,
            status='live',
            title__icontains=keyword,
        )|Q(
            category=category,
            city=city,
            status='live',
            body__icontains=keyword,
        )).order_by('-posted')
            
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
    context['category'] = category
    context['categories'] = categories
    context['all_ads'] = all_ads
    context['first_more_ad_id'] = first_more_ad_id
    context['sponsored_ads'] = sponsored_ads
    context['keyword'] = keyword

    layout = request.GET.get('layout', '')
    if layout == 'gallery':
        return render(request, 'ads/search_results_gallery.html', context)

    return render(request, 'ads/search_results.html', context)

@transaction.atomic
def contact(request):
    context = {}
    context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
    if request.method == 'POST':
        recaptcha = request.POST.get('g-recaptcha-response', '')
        if recaptcha:
            payload = {}
            payload['response'] = recaptcha
            payload['secret'] = settings.RECAPTCHA_SECRET_KEY
            r = requests.post(settings.RECAPTCHA_VERIFY_URL, data=payload)
            if not r.json()['success']:
                return redirect(site_url + '/contact/')
        else:
            return redirect(site_url + '/contact/')
        email = request.POST['email']
        try:
            validate_email(email)
        except:
            return redirect(site_url + '/contact/')
        message = request.POST['message']
        contact = ContactUs(email=email, message=message)
        contact.save()
        context['success'] = True
        return render(request, 'ads/contact.html', context)

    return render(request, 'ads/contact.html', context)

@transaction.atomic
def report_ad(request, section, ad_id):
    if section == 'leisure':
        try:
            ad = LeisureAd.objects.get(id=ad_id)
        except:
            ad = ScrapedAd.objects.get(id=ad_id)
    elif section == 'services':
        ad = ServicesAd.objects.get(id=ad_id)
    elif section == 'jobs':
        ad = JobsAd.objects.get(id=ad_id)
    elif section == 'sale':
        ad = SaleAd.objects.get(id=ad_id)
    elif section == 'housing':
        ad = HousingAd.objects.get(id=ad_id)
    elif section == 'community':
        ad = CommunityAd.objects.get(id=ad_id)
    else:
        return redirect('/')

    cookie_cityid = request.COOKIES.get(cookie_cityid_name, '')

    if not cookie_cityid:
        return redirect(site_url + '/all-cities/')

    city = City.objects.get(id=cookie_cityid)    
    nearby_cities = City.objects.filter(short_state=city.short_state)
    if isinstance(ad, ScrapedAd):
        category = AdCategory.objects.get(slug='escorts')
    else:
        category = ad.category

    categories = AdCategory.objects.filter(section=category.section)

    context = {}
    context['ad'] = ad
    context['city'] = city
    context['city_url'] = city.get_city_url()
    context['nearby_cities'] = nearby_cities
    context['categories'] = categories
    context['category'] = category
    context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY

    if request.method == 'POST':
        recaptcha = request.POST.get('g-recaptcha-response', '')
        if recaptcha:
            payload = {}
            payload['response'] = recaptcha
            payload['secret'] = settings.RECAPTCHA_SECRET_KEY
            r = requests.post(settings.RECAPTCHA_VERIFY_URL, data=payload)
            if not r.json()['success']:
                return redirect(site_url)
        else:
            return redirect(site_url)
        flag_message = request.POST.get('violationFlag', '')
        if not flag_message:
            return redirect(site_url)
        ReportAd(flag_message=flag_message, content_object=ad).save()
        return render(request, 'ads/reportad_success.html', context)

    return render(request, 'ads/reportad.html', context)

def help(request):
    return render(request, 'ads/help.html', {})

def privacy_policy(request):
    return render(request, 'ads/privacy_policy.html', {})

def terms_of_use(request):
    return render(request, 'ads/terms.html', {})

def safety(request):
    return render(request, 'ads/safety.html', {})

def custom404(request):
    response = render(request, 'ads/custom404.html', {})
    response.status_code = 404
    return response

def custom500(request):
    response = render(request, 'ads/custom500.html', {})
    response.status_code = 500
    return response
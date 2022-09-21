from django.shortcuts import render, redirect
from django.conf import settings
from geocity.models import City
from ads.models import AdCategory
from django.utils import timezone
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import password_validation as validator
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from .models import MainUser
from leisure.models import LeisureAd
from community.models import CommunityAd
from housing.models import HousingAd
from jobs.models import JobsAd
from sale.models import SaleAd
from services.models import ServicesAd
from itertools import chain
from sparkpost import SparkPost
from .models import CreditPurchase
from raven.contrib.django.raven_compat.models import client as raven_client
import pytz
import requests
import stripe
import utils
import uuid

cookie_city_id = settings.COOKIE_CITY_ID
site_url = settings.SITE_URL

@login_required
def account(request):
    user = request.user
    leisure_ads = LeisureAd.objects.filter(creator=user).exclude(status='removedbyuser').order_by('-posted')
    community_ads = CommunityAd.objects.filter(creator=user).exclude(status='removedbyuser').order_by('-posted')
    housing_ads = HousingAd.objects.filter(creator=user).exclude(status='removedbyuser').order_by('-posted')
    jobs_ads = JobsAd.objects.filter(creator=user).exclude(status='removedbyuser').order_by('-posted')
    sale_ads = SaleAd.objects.filter(creator=user).exclude(status='removedbyuser').order_by('-posted')
    services_ads = ServicesAd.objects.filter(creator=user).exclude(status='removedbyuser').order_by('-posted')
    all_ads = list(chain(
        leisure_ads, community_ads,
        housing_ads, jobs_ads,
        sale_ads, services_ads,
    ))

    context = {}
    context['credits'] = format(float(user.credits) / 100, '.2f')
    context['all_ads'] = all_ads
    context['ad_count'] = len(all_ads)
    return render(request, 'account/account.html', context)

def login(request):
    if request.user.is_authenticated:
        return redirect(site_url + '/account/')

    if request.method == 'POST':
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        user = authenticate(email=email, password=password)
        if user is not None:
            auth_login(request, user)
            next_url = request.POST.get('next', '')
            if next_url:
                return redirect(next_url)
            return redirect(site_url + '/account/')
        else:
            context = {}
            context['error'] = True
            context['email'] = email
            return render(request, 'account/login.html', context)
    next_url = request.GET.get('next', '')
    return render(request, 'account/login.html', {'next': next_url})

def create(request):
    if request.user.is_authenticated:
        return redirect(site_url + '/account/')

    context = {}
    context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
    if request.method == 'POST':
        email = request.POST.get('email', '')
        email_confirm = request.POST.get('email_confirm', '')
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        agree_to_terms = request.POST.get('termsAgreement', '')

        if email != email_confirm:
            context['emailmatch_error'] = True
            context['email'] = email
            return render(request, 'account/create.html', context)
        if password != password_confirm:
            context['passwordmatch_error'] = True
            context['email'] = email
            return render(request, 'account/create.html', context)
        try:
            validator.validate_password(password)
        except:
            context['weakpassword_error'] = True
            context['email'] = email
            return render(request, 'account/create.html', context)
        if agree_to_terms != 'true':
            context['terms_error'] = True
            context['email'] = email
            return render(request, 'account/create.html', context)

        recaptcha = request.POST.get('g-recaptcha-response', '')
        if recaptcha:
            try:
                u = MainUser.objects.get(email=email)
                context['userexists_error'] = True
                return render(request, 'account/create.html', context)
            except:
                pass
            payload = {}
            payload['response'] = recaptcha
            payload['secret'] = settings.RECAPTCHA_SECRET_KEY
            r = requests.post(settings.RECAPTCHA_VERIFY_URL, data=payload)
            if r.json()['success']:
                user = MainUser.objects.create_user(email=email, password=password)
                auth_login(request, user)
                return redirect(site_url + '/account/')
            else:
                context['recaptcha_error'] = True
                context['email'] = email
                return render(request, 'account/create.html', context)
        else:
            context['recaptcha_error'] = True
            return render(request, 'account/create.html', context)

    return render(request, 'account/create.html', context)

@login_required
def change_password(request):
    if request.method == 'POST':
        password_old = request.POST.get('password_old', '')
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        context = {}
        if password != password_confirm:
            context['passwordmatch_error'] = True
            return render(request, 'account/change_password.html', context)
        try:
            validator.validate_password(password)
        except:
            context['weakpassword_error'] = True
            return render(request, 'account/change_password.html', context)

        if password_old == password:
            context['samepassword_error'] = True
            return render(request, 'account/change_password.html', context)

        user = authenticate(email=request.user.email, password=password_old)
        if user is not None:
            user.set_password(password)
            user.save()
            context['passwordchange_success'] = True
            return render(request, 'account/change_password.html', context)
        else:
            context['invalidpassword_error'] = True
            return render(request, 'account/change_password.html', context)

    return render(request, 'account/change_password.html', {})

def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect(site_url + '/account/change-password/')

    if request.method == 'POST':
        context = {}
        email = request.POST.get('email', '')
        try:
            user = MainUser.objects.get(email=email)
            token = uuid.uuid4()
            user.password_reset_token = token
            user.save()
        except:
            context['emailnotfound_error'] = True
            return render(request, 'account/password_reset_request.html', context)

        subject = 'Reset your password'
        html_message = '<html><body><h4>Hi {},<br><br>'.format(email)
        html_message += 'Please click the link below to reset your password:<br><br>'
        html_message += '{}<br><br>'.format(site_url + '/account/password-reset/' + str(token))
        html_message += 'Thanks,<br><br>'
        html_message += '{}</h4></body></html>'.format(site_url)
        from_email = '{} <{}>'.format(settings.PROJECT_NAME, settings.EMAIL_FROM)
        sp = SparkPost(settings.SPARKPOST_API_KEY)
        response = sp.transmissions.send(
            recipients=[email],
            html=html_message,
            from_email=from_email,
            subject=subject,
            track_opens=True,
            track_clicks=True,
        )
        try:
            response['total_accepted_recipients']
        except Exception:
            raven_client.captureException()
            pass
        context['emailsent_success'] = True
        return render(request, 'account/password_reset_request.html', context)

    return render(request, 'account/password_reset_request.html', {})

def password_reset(request, token):
    context = {}
    tok = token.replace('/', '').strip()
    context['token'] = tok
    if request.method == 'POST':
        password_old = request.POST.get('password_old', '')
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if password != password_confirm:
            context['passwordmatch_error'] = True
            return render(request, 'account/password_reset.html', context)
        try:
            validator.validate_password(password)
        except:
            context['weakpassword_error'] = True
            return render(request, 'account/password_reset.html', context)

        try:
            user = MainUser.objects.get(password_reset_token=tok)
            user.set_password(password)
            user.save()
            context['passwordchange_success'] = True
            return render(request, 'account/password_reset.html', context)
        except:
            context['invalidtoken_error'] = True
            return render(request, 'account/password_reset.html', context)

    return render(request, 'account/password_reset.html', context)

@login_required
def buy_credits(request):
    context = {}
    if request.method == 'POST':
        token = request.POST.get('stripeTokenDone', '')
        if token:
            amount = int(request.POST['amount'].strip())
            recaptcha = request.POST.get('g-recaptcha-response', '')
            if not recaptcha:
                context['token'] = token
                context['amount'] = amount
                context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
                context['try_again_error'] = True
                return render(request, 'account/buy_credits_confirm.html', context)
            payload = {}
            payload['response'] = recaptcha
            payload['secret'] = settings.RECAPTCHA_SECRET_KEY
            r = requests.post(settings.RECAPTCHA_VERIFY_URL, data=payload)
            if not r.json()['success']:
                context['token'] = token
                context['amount'] = amount
                context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
                context['try_again_error'] = True
                return render(request, 'account/buy_credits_confirm.html', context)

            agree_to_terms = request.POST.get('termsAgreement', '')
            if agree_to_terms != 'true':
                context['token'] = token
                context['amount'] = amount
                context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
                context['try_again_error'] = True
                return render(request, 'account/buy_credits_confirm.html', context)
            stripe.api_key = settings.STRIPE_SK
            try:
                charge = stripe.Charge.create(
                    amount=amount,
                    currency="usd",
                    description="Account funding",
                    source=token,
                )
            except Exception:
                raven_client.captureException()
                return redirect(site_url + '/account/buy-credits/')
            user = request.user
            user.credits = user.credits + amount
            user.save()
            purchase = CreditPurchase(user=user)
            purchase.paid = True
            purchase.amount = charge.amount
            purchase.stripe_charge_id = charge.id
            purchase.payment_method = 'stripe'
            purchase.save()
            context['email'] = user.email
            context['amount'] = format(float(amount) / 100, '.2f')
            return render(request, 'account/buy_credits_success.html', context)
        amount = request.POST['amount'].replace('$', '').replace(',', '')
        try:
            amount = float("%.2f" % round(float(amount), 2))
        except Exception:
            raven_client.captureException()
            return redirect(site_url + '/account/buy-credits/')
        amount = int(amount * 100)
        if amount < 500:
            return redirect(site_url + '/account/buy-credits/')
        token = request.POST['stripeToken']
        context['token'] = token
        context['amount'] = amount
        context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
        return render(request, 'account/buy_credits_confirm.html', context)


    credits = format(float(request.user.credits) / 100, '.2f')
    context['credits'] = credits 
    context['stripe_key'] = settings.STRIPE_PK
    return render(request, 'account/buy_credits.html', context)

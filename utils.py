from __future__ import unicode_literals
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from cStringIO import StringIO
from PIL import Image
from sparkpost import SparkPost
from django.db import connection
from threading import Thread
import boto3
import json
import uuid
import requests
import datetime
import tldextract

site_url = settings.SITE_URL
domain = settings.DOMAIN
image_specs = settings.IMAGE_SPECS
project_name = settings.PROJECT_NAME

def postpone(function):
  def decorator(*args, **kwargs):
    t = Thread(target = function, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
  return decorator

@csrf_exempt
def upload_img(request):
    original_img = Image.open(request.FILES['image'])
    bucket = settings.S3_IMG_BUCKET
    img_id = str(uuid.uuid4())
    img_name = '%s.jpg' % img_id
    s3 = boto3.client('s3')
    data = {}
    try:
        for spec in image_specs.values():
            temp_img = original_img.copy()
            temp_img.thumbnail(spec['size'])
            out_img = StringIO()
            temp_img.save(out_img, "JPEG")
            key = '%s/%s' % (spec['folder'], img_name)
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=out_img.getvalue(),
                ContentType='image/jpeg',
            )
            if spec['folder'] == 'small':
                data['url'] = 'https://s3.amazonaws.com/%s/%s' % (bucket, key)
                width, height = temp_img.size
                data['width'] = width
                data['height'] = height
                data['name'] = img_name
                data['origName'] = request.POST['origName']
            temp_img.close()
            out_img.close()
    except Exception, err:
        data['error'] = err
    finally:
        original_img.close()

    return HttpResponse(json.dumps(data), content_type='application/json')

@postpone
@csrf_exempt
def send_newad_email(ad, cat, **kwargs):
    subject = 'New posting: %s... | %s' % (ad.title[:25], settings.PROJECT_NAME)
    view_link = ad.get_ad_url()
    market = '%s.%s' % (ad.city_short_name, settings.DOMAIN)
    if cat.slug in ['escorts', 'body-rubs', 'strippers-strip-clubs']:
        edit_link = '%s/post-ad/%s/%s/?token=%s&region=%s' % (site_url, cat.slug, 
            cat.id, ad.edit_token, ad.city_id)
    else:
        edit_link = '%s/post-ad/%s/%s/?token=%s&region=%s' % (site_url, cat.section, 
            cat.id, ad.edit_token, ad.city_id)
    html_message = '<html><body><p>Hi %s,</p>' % ad.email
    html_message += '<p>Thank you for posting with us! Your posting is live.</p>'
    html_message += '<p>Use the link below to view your ad:<br>'
    html_message += '<a href="%s">%s</a></p>' % (view_link, view_link)
    html_message += '<p>Manage your ad by clicking on the link below:<br>'
    html_message += '<a href="%s">%s</a></p>' % (edit_link, edit_link)
    if kwargs:
        order = kwargs['order']
        html_message += '<p>Market: <b>%s</b><br>' % market
        if order.freedom_plan:
            html_message += 'Freedom plan: <b>30 days</b><br>'
        if order.times_to_move != '0':
            html_message += 'MoveUP hours: <b>%s</b><br>' % order.times_to_move
        if order.sponsored_weeks != '0':
            html_message += 'Sponsored weeks: <b>%s</b></p>' % order.sponsored_weeks
    html_message += '<p><b><span style="color:green;">DO NOT DELETE THIS EMAIL</span></b>'
    html_message += ' - you might need this link to manage your ad in the future.</p>'
    html_message += '<p>Thanks,<br>'
    html_message += '%s</p></body></html>' % project_name
    from_email = '%s <%s>' % (market, settings.EMAIL_FROM)
    sp = SparkPost(settings.SPARKPOST_API_KEY)
    response = sp.transmissions.send(
        recipients=[ad.email],
        html=html_message,
        from_email=from_email.replace(':8000', ''),
        subject=subject,
    )
    connection.close()

def render_with_cookie(response, city):
    max_age = 365 * 24 * 60 * 60  #one year
    expire_date = datetime.datetime.strftime(
        datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age), 
        "%a, %d-%b-%Y %H:%M:%S GMT"
    )
    response.set_cookie(settings.COOKIE_CITY_ID, city.id, 
        domain=settings.SESSION_COOKIE_DOMAIN,
        expires=expire_date,
        httponly=True,
    )
    return response

def get_subdomain(request):
    subdomain = tldextract.extract(request.build_absolute_uri()).subdomain
    subdomain = subdomain.replace('www.', '').replace('www-staging', '').replace('.', '')
    return subdomain

def extract_cellnumber(text):
    import re
    r = re.compile(r'(\d{3})\D*(\d{3})\D*(\d{4})')
    results = r.findall(text)
    if results:
        return '+1' + ''.join(results[0])
    else:
        return ''
# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-08-08 21:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='scrapedad',
            name='city_short_name',
            field=models.CharField(default='auburn', max_length=60),
            preserve_default=False,
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-08-07 00:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sale', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='salead',
            name='category_slug',
            field=models.SlugField(default='1'),
            preserve_default=False,
        ),
    ]

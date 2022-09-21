from __future__ import unicode_literals

from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser,
)
from django.db import models, transaction
from hashlib import md5
from random import random
from django.utils import timezone
from django.conf import settings
import uuid

class MainUserManager(BaseUserManager):
    def create_user(self, email, password):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')
        if not password:
            raise ValueError('Users must have a password')

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(email,
                                password=password,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class MainUser(AbstractBaseUser):
    email = models.EmailField(
        verbose_name='email address',
        max_length=50,
        unique=True,
    )
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    credits = models.IntegerField(default=0)
    password_reset_token = models.UUIDField( 
        default=uuid.uuid4, 
    )

    # NOTE: AbstractBaseUser provides last_login
    # last_login = models.DateTimeField(_('last login'), blank=True, null=True)

    objects = MainUserManager()

    USERNAME_FIELD = 'email'

    #subclasses of AbstractBaseUser must provide this method
    def get_full_name(self):
    	pass

    #subclasses of AbstractBaseUser must provide this method
    def get_short_name(self):
    	pass

    def get_email(self):
        return self.email

    def __str__(self):  # __unicode__ on Python 2
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    def get_last_login(self):
        return self.last_login

    @property
    def is_staff(self):
        return self.is_admin


class CreditPurchase(models.Model):
    user = models.ForeignKey(MainUser)
    order_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
    )
    order_date = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=True)
    payment_method = models.CharField(
        max_length=10,
        blank=True,
        default='',
        choices=settings.PAYMENT_METHOD_CHOICES,
    )
    amount = models.IntegerField(default=0)
    stripe_charge_id = models.CharField(max_length=30, blank=True, default='')

    def __str__(self):
        return '$%s, %s' % (str(self.amount / 100), self.order_date)




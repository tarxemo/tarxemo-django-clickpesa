"""
URL configuration for clickpesa app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('callback/payment/', views.payment_callback, name='payment_callback'),
    path('callback/payout/', views.payout_callback, name='payout_callback'),
]

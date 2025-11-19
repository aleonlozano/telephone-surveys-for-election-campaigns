from django.urls import path
from . import views

app_name = 'surveys'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:pk>/launch/', views.launch_campaign, name='launch_campaign'),
    path('contacts/', views.contact_list, name='contact_list'),
    path('calls/', views.call_list, name='call_list'),
    path('twilio/call/<int:call_id>/', views.twilio_call_webhook, name='twilio_call_webhook'),
]

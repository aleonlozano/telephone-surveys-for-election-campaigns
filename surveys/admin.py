from django.contrib import admin
from .models import Campaign, Contact, Call, Response

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'candidate_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'candidate_name')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'created_at')
    search_fields = ('name', 'phone_number')

@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'contact', 'status', 'preference', 'loyalty_score', 'created_at')
    list_filter = ('status', 'campaign')
    search_fields = ('contact__phone_number', 'campaign__name', 'preference')

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('call', 'question_text', 'created_at')
    search_fields = ('question_text', 'answer_raw')

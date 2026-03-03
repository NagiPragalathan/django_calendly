from django.shortcuts import render, redirect
from base.models import Settings, ZohoToken, SmtpSettings, PreFillMapping, CalendlyCredentials
from django.contrib.auth.decorators import login_required
from base.routes.tool_kit.zoho_tool import get_event_fields, check_access_token_validity, get_access_token, create_event_field, get_module_fields, create_module_field
from Finalty.settings import CLIENT_ID, CLIENT_SECRET
from django.contrib import messages
import json

# Global Orchestration Constants
INTEGRATION_FIELDS = [
    {'key': 'Calendly_Event_Uri', 'label': 'Event URI'},
    {'key': 'Calendly_Invitee_Uri', 'label': 'Invitee URI'},
    {'key': 'Calendly_Cancel_Url', 'label': 'Cancel URL'},
    {'key': 'Calendly_Reschedule_Url', 'label': 'Reschedule URL'},
    {'key': 'Calendly_Event_Status', 'label': 'Event Status'},
    {'key': 'Calendly_Question_Answer', 'label': 'Questions & Answers'},
    {'key': 'External_Event_ID', 'label': 'External Event ID (Google/Outlook)'},
    {'key': 'Meeting_Venue', 'label': 'Meeting Venue (Virtual/In-Person)'},
]




@login_required
def settings_form(request):
    """Handles both creating and updating user settings."""
    user = request.user
    settings_instance = Settings.objects.filter(user=user).first()
    
    # Fetch existing Zoho fields for mapping
    zoho_fields = []
    zoho_token = ZohoToken.objects.filter(user=user).first()
    access_token = None
    
    try:
        if zoho_token:
            access_token = zoho_token.access_token
            if not check_access_token_validity(access_token):
                access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
                ZohoToken.objects.filter(user=user).update(access_token=access_token)
            
            fields_data = get_event_fields(access_token)
            if "fields" in fields_data:
                for f in fields_data["fields"]:
                    if f.get("data_type") in ["text", "textarea", "url"]:
                        zoho_fields.append({
                            "api_name": f["api_name"],
                            "label": f["field_label"]
                        })
                zoho_fields.sort(key=lambda x: x["label"])
    except Exception as e:
        print(f"Error fetching Zoho fields: {e}")
    # Fetch Lead fields for pre-fill mapping
    lead_fields = []
    try:
        if access_token:
            lead_data = get_module_fields(access_token, "Leads")
            if "fields" in lead_data:
                for f in lead_data["fields"]:
                    lead_fields.append({"api_name": f["api_name"], "label": f["field_label"]})
                lead_fields.sort(key=lambda x: x["label"])
    except: pass

    # Get SMTP Settings
    smtp_settings = SmtpSettings.objects.filter(user=user).first()
    
    if request.method == "POST":
        # ... existing logic for Settings model ...
        leads_to_store = request.POST.get("leads_to_store")
        lead_source = request.POST.get("lead_source")
        use_default_mapping = request.POST.get("use_default_mapping") == "on"
        
        field_mappings = {}

        for item in INTEGRATION_FIELDS:
            create_name = request.POST.get(f"create_{item['key']}")
            if create_name and access_token:
                try:
                    create_res = create_module_field(access_token, leads_to_store, create_name)
                    if create_res.get("fields") and create_res["fields"][0].get("api_name"):
                        field_mappings[item['key']] = create_res["fields"][0]["api_name"]
                except: pass
            else:
                val = request.POST.get(f"map_{item['key']}")
                if val: field_mappings[item['key']] = val

        Settings.objects.update_or_create(user=user, defaults={
            'leads_to_store': leads_to_store,
            'lead_source': lead_source,
            'use_default_mapping': use_default_mapping,
            'field_mappings': field_mappings
        })

        # Handle SMTP
        SmtpSettings.objects.update_or_create(user=user, defaults={
            'smtp_server': request.POST.get('smtp_server'),
            'smtp_port': request.POST.get('smtp_port', 587),
            'smtp_user': request.POST.get('smtp_user'),
            'smtp_password': request.POST.get('smtp_password'),
            'use_tls': request.POST.get('use_tls') == 'on'
        })

    return render(request, "settings_form.html", {
        "settings": settings_instance,
        "zoho_fields": zoho_fields,
        "lead_fields": lead_fields,
        "integration_fields": INTEGRATION_FIELDS,
        "smtp_settings": smtp_settings
    })

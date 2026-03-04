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
    # UTM Intelligence Parameters
    {'key': 'utm_source', 'label': 'UTM Source'},
    {'key': 'utm_medium', 'label': 'UTM Medium'},
    {'key': 'utm_campaign', 'label': 'UTM Campaign'},
    {'key': 'utm_content', 'label': 'UTM Content'},
    {'key': 'utm_term', 'label': 'UTM Term'},
]

@login_required
def settings_form(request):
    """Handles both creating and updating user settings."""
    user = request.user
    settings_instance = Settings.objects.filter(user=user).first()
    
    # Identify Active Hub Node
    from base.utils import get_active_hub
    active_hub = get_active_hub(request)
    
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
    
    # Retrieve Webhook Intelligence for Active Hub
    webhook_status = []
    if active_hub and active_hub.access_token:
        try:
            from base.routes.tool_kit.calendly_tool import CalendlyWebhookManager
            wh_manager = CalendlyWebhookManager(active_hub.access_token)
            
            # Fetch User Scoped Webhooks
            user_wh = wh_manager.list_webhooks(scope="user")
            if user_wh.get('success'):
                webhook_status.extend(user_wh.get('data', []))
                
            # Fetch Organization Scoped Webhooks
            if wh_manager.organization_url:
                org_wh = wh_manager.list_webhooks(scope="organization")
                if org_wh.get('success'):
                    # Avoid duplicates if any, though likely distinct
                    existing_uris = {w['uri'] for w in webhook_status}
                    for w in org_wh.get('data', []):
                        if w['uri'] not in existing_uris:
                            webhook_status.append(w)
        except Exception as e:
            print(f"Webhook List Error: {e}")

    if request.method == "POST":
        action = request.POST.get('webhook_action')
        global_action = request.POST.get('global_action')
        webhook_id = request.POST.get('webhook_id')

        # 1. Action: Webhook Decommissioning
        if action == 'delete' and webhook_id and active_hub:
            try:
                from base.routes.tool_kit.calendly_tool import CalendlyWebhookManager
                wh_manager = CalendlyWebhookManager(active_hub.access_token)
                res = wh_manager.delete_webhook(webhook_id.split('/')[-1])
                if res.get('success'): 
                    messages.success(request, "Real-time data stream decommissioned successfully.")
                else: 
                    messages.error(request, f"Gateway Rejection: {res.get('error')}")
                return redirect('settings_form')
            except Exception as e:
                messages.error(request, f"Webhook Operational Failure: {str(e)}")

        # 2. Action: Force Webhook Synchronization (Manual Trigger)
        if action == 'refresh' and active_hub:
            try:
                from base.routes.tool_kit.calendly_tool import CalendlyWebhookManager
                from Finalty.settings import BASE_WEBHOOK_URL
                wh_manager = CalendlyWebhookManager(active_hub.access_token)
                
                # Determine effective base URL (UI Value > Settings Config)
                effective_base = settings_instance.webhook_base_url if settings_instance and settings_instance.webhook_base_url else BASE_WEBHOOK_URL
                
                # Webhook creation via manager (automatically handles user/org URIs)
                target_url = f"{effective_base.rstrip('/')}/calendly-webhook/meeting/{active_hub.unique_id}/{request.user.id}/"
                events = ["invitee.created", "invitee.canceled", "invitee_no_show.created", "invitee_no_show.deleted"]
                
                # Try organizational scope first
                res = wh_manager.create_webhook(target_url, events, scope="organization")
                if not res.get('success'):
                    # Fallback to user scope
                    res = wh_manager.create_webhook(target_url, events, scope="user")
                
                if res.get('success'):
                    messages.success(request, f"Automated data streams initialized for node {active_hub.email}")
                else:
                    messages.error(request, f"Gateway synchronization failed: {res.get('error')}")
                return redirect('settings_form')
            except Exception as e:
                messages.error(request, f"Sync Hub Failure: {str(e)}")

        # 3. Action: Save Global Directives
        if global_action == "save" or not action: # Default fallback to save
            leads_to_store = request.POST.get("leads_to_store")
            lead_source = request.POST.get("lead_source")
            use_default_mapping = request.POST.get("use_default_mapping") == "on"
            webhook_base_url = request.POST.get("webhook_base_url")
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
                'field_mappings': field_mappings,
                'webhook_base_url': webhook_base_url
            })

            SmtpSettings.objects.update_or_create(user=user, defaults={
                'smtp_server': request.POST.get('smtp_server'),
                'smtp_port': int(request.POST.get('smtp_port', 587)),
                'smtp_user': request.POST.get('smtp_user'),
                'smtp_password': request.POST.get('smtp_password'),
                'use_tls': request.POST.get('use_tls') == 'on'
            })
            
            messages.success(request, "Global synchronization directives deployed and active.")
            return redirect('settings_form')

    return render(request, "settings_form.html", {
        "settings": settings_instance,
        "zoho_fields": zoho_fields,
        "lead_fields": lead_fields,
        "integration_fields": INTEGRATION_FIELDS,
        "smtp_settings": smtp_settings,
        "active_hub": active_hub,
        "webhook_status": webhook_status
    })

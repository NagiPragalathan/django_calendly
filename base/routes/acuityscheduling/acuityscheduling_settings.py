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
    
    # Retrieve Webhook Intelligence for ALL Hubs
    webhook_status = []
    print(f"\n--- [DEBUG] Global Webhook Fetch Start ---")
    print(f"User: {user.email}")
    
    try:
        from base.routes.tool_kit.calendly_tool import CalendlyWebhookManager, CalendlyTokenManager
        token_manager = CalendlyTokenManager()
        all_hubs = CalendlyCredentials.objects.filter(email=request.user.email)
        
        for hub in all_hubs:
            print(f"Processing Hub: {hub.email} (ID: {hub.unique_id})")
            if not hub.access_token:
                print(f"Skipping {hub.email}: No access token.")
                continue
                
            valid_token, err = token_manager.get_valid_access_token(hub.unique_id, hub.email)
            if not valid_token:
                print(f"Skipping {hub.email}: Token validation failed: {err}")
                continue
                
            try:
                wh_manager = CalendlyWebhookManager(valid_token)
                hub_display_name = wh_manager.user_name or hub.company_name or hub.email
                
                # Fetch User Scoped Webhooks
                user_wh = wh_manager.list_webhooks(scope="user")
                if user_wh.get('success'):
                    data = user_wh.get('data', [])
                    print(f"Fetched {len(data)} user hooks for {hub.email}")
                    for w in data:
                        w['hub_name'] = hub_display_name
                        w['hub_id'] = str(hub.unique_id)
                        webhook_status.append(w)
                        
                # Fetch Organization Scoped Webhooks
                if wh_manager.organization_url:
                    org_wh = wh_manager.list_webhooks(scope="organization")
                    if org_wh.get('success'):
                        data = org_wh.get('data', [])
                        print(f"Fetched {len(data)} org hooks for {hub.email}")
                        existing_uris = {w['uri'] for w in webhook_status}
                        for w in data:
                            if w['uri'] not in existing_uris:
                                w['hub_name'] = hub_display_name
                                w['hub_id'] = str(hub.unique_id)
                                webhook_status.append(w)
            except Exception as e:
                print(f"Webhook Manager Error for {hub.email}: {repr(e)}")
    except Exception as e:
        print(f"Global Webhook Fetch Fatal Error: {repr(e)}")
    print(f"--- [DEBUG] Global Webhook Fetch End. Total: {len(webhook_status)} ---\n")

    if request.method == "POST":
        action = request.POST.get('webhook_action')
        global_action = request.POST.get('global_action')
        webhook_id = request.POST.get('webhook_id')
        webhook_hub_id = request.POST.get('webhook_hub_id')

        # Find target hub for operations
        target_hub = active_hub
        if webhook_hub_id:
            target_hub = CalendlyCredentials.objects.filter(unique_id=webhook_hub_id, email=request.user.email).first()

        # 1. Action: Webhook Decommissioning
        if action == 'delete' and webhook_id and target_hub:
            try:
                from base.routes.tool_kit.calendly_tool import CalendlyWebhookManager, CalendlyTokenManager
                token_manager = CalendlyTokenManager()
                valid_token, err = token_manager.get_valid_access_token(target_hub.unique_id, target_hub.email)
                if valid_token:
                    wh_manager = CalendlyWebhookManager(valid_token)
                    res = wh_manager.delete_webhook(webhook_id.split('/')[-1])
                    if res.get('success'): 
                        messages.success(request, "Real-time data stream decommissioned successfully.")
                    else: 
                        messages.error(request, f"Gateway Rejection: {res.get('error')}")
                return redirect('settings_form')
            except Exception as e:
                messages.error(request, f"Webhook Operational Failure: {str(e)}")

        # 2. Action: Force Webhook Synchronization (Manual Trigger)
        if action == 'refresh':
            # Target ONLY the active hub by default as per user request
            target_hubs = [target_hub] if target_hub else []
            
            for hub in target_hubs:
                if not hub or not hub.access_token: continue
                try:
                    from base.routes.tool_kit.calendly_tool import CalendlyWebhookManager, CalendlyTokenManager
                    token_manager = CalendlyTokenManager()
                    valid_token, err = token_manager.get_valid_access_token(hub.unique_id, hub.email)
                    if not valid_token: continue

                    wh_manager = CalendlyWebhookManager(valid_token)
                    
                    # 1. Prioritize active POST submission over saved settings over default host
                    form_url = request.POST.get('webhook_base_url', '').strip()
                    if form_url:
                        effective_base = form_url
                    elif settings_instance and settings_instance.webhook_base_url:
                        effective_base = settings_instance.webhook_base_url
                    else:
                        effective_base = request.build_absolute_uri('/')[:-1]
                    
                    # 2. Calendly strictly forbids localhost or non-HTTPS domains. Catch this before calling Calendly.
                    if not effective_base.startswith('https://'):
                        messages.error(request, f"Gateway Rejection for {hub.company_name or hub.email}: Calendly strictly requires a public HTTPS Tunnel URL (e.g., ngrok/Vercel). Please enter a valid HTTPS URL in the 'Public Tunnel URL' field above.")
                        continue
                        
                    target_url = f"{effective_base.rstrip('/')}/calendly-webhook/meeting/{hub.unique_id}/{request.user.id}/"
                    events = ["invitee.created", "invitee.canceled", "invitee_no_show.created", "invitee_no_show.deleted"]
                    
                    # 3. Try to establish organization-wide scope (requires admin logic)
                    res = wh_manager.create_webhook(target_url, events, scope="organization")
                    
                    # If organization fails (e.g., unauthorized scope), fallback to user scope
                    if not res.get('success'):
                        user_res = wh_manager.create_webhook(target_url, events, scope="user")
                        if user_res.get('success'):
                            res = user_res
                        else:
                            # Append user error onto organization error to show the complete failure context
                            res['error'] = f"Org Scope Failed: {res.get('error')} | User Scope Failed: {user_res.get('error')}"
                    
                    hub_display_name = wh_manager.user_name or hub.company_name or hub.email
                    if res.get('success'):
                        messages.success(request, f"Automated data streams initialized for node: {hub_display_name}")
                    else:
                        messages.error(request, f"Gateway synchronization failed for {hub_display_name}: {res.get('error')}")
                except Exception as e:
                    messages.error(request, f"Sync Hub Failure: {str(e)}")
            return redirect('settings_form')

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

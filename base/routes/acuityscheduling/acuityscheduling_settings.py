from django.shortcuts import render, redirect
from base.models import Settings, ZohoToken
from django.contrib.auth.decorators import login_required
from base.routes.tool_kit.zoho_tool import get_event_fields, check_access_token_validity, get_access_token, create_event_field
from Finalty.settings import CLIENT_ID, CLIENT_SECRET
from django.contrib import messages
import json


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

    # Standard Integration Fields for Mapping
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

    if request.method == "POST":
        leads_to_store = request.POST.get("leads_to_store")
        lead_source = request.POST.get("lead_source")
        
        # Handle field mappings from POST
        field_mappings = {}
        for item in INTEGRATION_FIELDS:
            # Check if creating a new field
            create_name = request.POST.get(f"create_{item['key']}")
            if create_name and access_token:
                # API call to create field in Zoho
                try:
                    create_res = create_event_field(access_token, create_name)
                    if create_res.get("fields") and create_res["fields"][0].get("api_name"):
                        field_mappings[item['key']] = create_res["fields"][0]["api_name"]
                    else:
                        messages.warning(request, f"Could not create field '{create_name}' in Zoho. Falling back to default.")
                except Exception as e:
                    print(f"Auth error creating field: {e}")
            else:
                # Use selected existing field
                val = request.POST.get(f"map_{item['key']}")
                if val:
                    field_mappings[item['key']] = val

        if settings_instance:
            Settings.objects.filter(user=user).update(
                leads_to_store=leads_to_store,
                lead_source=lead_source,
                field_mappings=field_mappings
            )
        else:
            Settings.objects.create(
                user=user,
                leads_to_store=leads_to_store,
                lead_source=lead_source,
                field_mappings=field_mappings
            )
        
        messages.success(request, "Integration logic and field orchestration updated successfully!")
        return redirect("settings_form")

    return render(request, "settings_form.html", {
        "settings": settings_instance,
        "zoho_fields": zoho_fields,
        "integration_fields": INTEGRATION_FIELDS
    })

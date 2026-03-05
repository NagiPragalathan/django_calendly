from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import requests
import json
import logging
from base.models import CalendlyCredentials, Settings
from base.routes.tool_kit.zoho_tool import check_and_add_email, add_meeting_to_zoho_crm, update_meeting_in_zoho_crm, delete_meeting_from_zoho_crm


# Logger for debugging
logger = logging.getLogger(__name__)

# Base URL for Acuity API
BASE_URL = "https://acuityscheduling.com/api/v1"

def get_appointment_details(credential_id, appointment_id):
    """
    Fetch appointment details from Acuity Scheduling API.
    """
    try:
        # Fetch credentials for the authenticated user
        data_obj = CalendlyCredentials.objects.get(unique_id=credential_id)

        # Make API call to Acuity
        url = f"{BASE_URL}/appointments/{appointment_id}"
        response = requests.get(url, auth=(data_obj.user_id, data_obj.api_key))

        if response.status_code == 200:
            appointment_data = response.json()
            print(appointment_data)

            # Extract candidate name and appointment type ID
            candidate_name = f"{appointment_data.get('firstName', '')} {appointment_data.get('lastName', '')}"
            formsText = appointment_data.get("formsText", '')
            appointment_type_id = appointment_data.get("appointmentTypeID")
            type_name = appointment_data.get("type", {})

            # Log details to the console
            logger.info(f"Candidate Name: {candidate_name}")
            logger.info(f"Appointment Type Name: {type_name}")
            logger.info(f"Appointment Type ID: {appointment_type_id}")

            return appointment_data
        else:
            logger.error(f"Failed to fetch appointment details: {response.status_code}")
            logger.error(response.json())
            return None
    except CalendlyCredentials.DoesNotExist:
        logger.error("Calendly Credentials not found for the user.")
        return None
    except Exception as e:
        logger.error(f"Error while fetching appointment details: {e}")
        return None


@csrf_exempt
def calendly_webhook_create_meeting(request, credential_id, user_id):
    """
    View to handle incoming webhooks from Calendly.
    Supports created, canceled, and rescheduled appointments.
    """
    Module = "Contacts"
    app_user_id = user_id
    
    if request.method == "POST":
        try:
            # Parse JSON data from Calendly
            data = json.loads(request.body)
            event_type = data.get("event")
            payload = data.get("payload", {})

            if not event_type or not payload:
                return JsonResponse({"message": "Missing required data payload."}, status=400)

            # 1. Settings Intelligence
            try:
                settings = Settings.objects.get(user=user_id) 
                Module = settings.leads_to_store
                field_mapping = settings.field_mappings or {}
            except Exception:
                settings = None
                Module = "Contacts"
                field_mapping = {}

            # 2. Advanced Extraction Logic
            scheduled_event = payload.get("scheduled_event", {})
            email = payload.get("email")
            full_name = payload.get("name", "").strip() or payload.get("first_name", "").strip()
            name_parts = full_name.split()
            first_name = name_parts[0] if name_parts else "Invitee"
            # Zoho MANDATORY: Last Name must not be empty
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "."

            # Tracking & Questions
            tracking = payload.get("tracking", {}) or {}
            qa_raw = payload.get("questions_and_answers", [])
            qa_text = "\n".join([f"Q{i+1}: {qa.get('question')}\nA{i+1}: {qa.get('answer') or '---'}\n" for i, qa in enumerate(qa_raw)])

            location = scheduled_event.get("location", {})
            location_type = location.get("type", "Virtual")
            join_url = location.get("join_url", "")

            # Hub Metadata
            hub_email = "Unknown"
            try:
                hub = CalendlyCredentials.objects.get(unique_id=credential_id)
                hub_email = hub.email
            except: pass

            # 3. Data Orchestration
            # Plain Paragraph Description for standard CRM view
            plain_description = f"Meeting scheduled with {full_name} ({email}) via Calendly. Event: {scheduled_event.get('name')}. Time: {scheduled_event.get('start_time')}."
            
            # Rich Details for Zoho Notes (Formatted)
            rich_details = f"""╔==================================================================╗
                         Meeting Flow Intelligence                          
╚==================================================================╝

• Event Type   : {scheduled_event.get('name')}
• Invitee Name : {full_name}
• Email        : {email}
• Start Time   : {scheduled_event.get('start_time')}
• Location     : {location_type}
• Join Link    : {join_url}

• Calendly Hub : {hub_email}
• Provider     : nanotom_calendly_sync

♕ Questions & Responses
───────────────────────
{qa_text if qa_text else '• No custom questions provided.'}

⚙ UTM Tracking Details
───────────────────────
• Source   : {tracking.get('utm_source', 'Direct')}
• Medium   : {tracking.get('utm_medium', 'Organic')}
• Campaign : {tracking.get('utm_campaign', 'None')}
• Content  : {tracking.get('utm_content', 'None')}
• Term     : {tracking.get('utm_term', 'None')}
"""

            # 4. Construct Event JSON with Mapping Awareness
            event_data = {
                "Event_Title": f"Meeting: {scheduled_event.get('name')} with {full_name}",
                "Subject": f"Meeting: {scheduled_event.get('name')} with {full_name}",
                "Start_DateTime": datetime.strptime(scheduled_event.get("start_time"), "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "End_DateTime": datetime.strptime(scheduled_event.get("end_time"), "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "Participants": [{"participant": email, "type": "email"}],
                "Location": join_url if join_url else location_type,
                "Description": plain_description,
                "Notes_Data": rich_details, # Custom key for tool handling
                "Who_Id": None,
                "Calendly_Event_URI": scheduled_event.get("uri"),
                "Calendly_Invitee_URI": payload.get("uri"),
                "Calendly_Cancel_URL": payload.get("cancel_url"),
                "Calendly_Reschedule_URL": payload.get("reschedule_url"),
                "Timezone": payload.get("timezone"),
            }

            # Apply Dynamic Field Mappings from User Settings
            mapping_blueprint = {
                'Calendly_Event_Uri': scheduled_event.get('uri'),
                'Calendly_Invitee_Uri': payload.get('uri'),
                'Calendly_Cancel_Url': payload.get('cancel_url'),
                'Calendly_Reschedule_Url': payload.get('reschedule_url'),
                'Calendly_Event_Status': payload.get('status', 'active'),
                'Calendly_Question_Answer': qa_text,
                'External_Event_ID': scheduled_event.get('external_id'),
                'Meeting_Venue': location_type,
                'send_status': 'Initial Sync Complete',
                'calendly_account': hub_email,
                'provider_name': 'nanotom_calendly_sync',
                'utm_source': tracking.get('utm_source'),
                'utm_medium': tracking.get('utm_medium'),
                'utm_campaign': tracking.get('utm_campaign'),
                'utm_content': tracking.get('utm_content'),
                'utm_term': tracking.get('utm_term'),
            }

            for internal_key, value in mapping_blueprint.items():
                target_field = field_mapping.get(internal_key)
                if target_field and value:
                    event_data[target_field] = value

            # 5. Execute Record Lifecycle
            who_id = check_and_add_email({"email": email, "firstName": first_name, "lastName": last_name, "app_user_id": user_id}, Module, user_id, only_contact=True)
            event_data["Who_Id"] = who_id

            if event_type == "invitee.created":
                print("🆕 Initiating creation sequence...")
                appointment_data_created = add_meeting_to_zoho_crm(event_data, app_user_id)
            elif event_type == "invitee.canceled":
                print("♻️ Initiating cancellation sequence...")
                appointment_data_created = delete_meeting_from_zoho_crm(scheduled_event.get("uri"), app_user_id)
            elif event_type == "invitee.rescheduled":
                print("🔄 Initiating reschedule sequence...")
                appointment_data_created = update_meeting_in_zoho_crm(event_data, app_user_id)

            return JsonResponse({"message": "Data stream synchronized.", "id": who_id})

        except Exception as e:
            logger.error(f"Sync Engine Critical Error: {e}")
            return JsonResponse({"message": f"Sync Failure: {str(e)}"}, status=500)
    return HttpResponseBadRequest("Unsupported request method.")

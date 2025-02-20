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
            event_type = data.get("event")  # 'invitee.created', 'invitee.canceled', etc.
            payload = data.get("payload", {})

            if not event_type or not payload:
                return JsonResponse({"message": "Missing required data in the webhook payload."}, status=400)

            # Extract appointment details from payload
            scheduled_event = payload.get("scheduled_event", {})
            
            try:
                settings = Settings.objects.get(user_id=user_id) 
                Module = settings.leads_to_store   
            except Exception as e:
                Module = "Contacts"
                
            print(f"Search the data in CRM of {Module}")

            # Extract participant details
            email = payload.get("email")
            name = payload.get("name", "").split()
            first_name = name[0] if name else payload.get("first_name", "")
            last_name = " ".join(name[1:]) if len(name) > 1 else payload.get("last_name", "")

            # Get location details
            location = scheduled_event.get("location", {})
            location_type = location.get("type", "")
            join_url = location.get("join_url", "")

            # Format questions and answers
            questions_and_answers = payload.get("questions_and_answers", [])
            description = "\n".join([
                f"Q: {qa['question']}\nA: {qa['answer']}"
                for qa in questions_and_answers
            ])

            # Convert datetime strings to datetime objects
            start_dt = datetime.strptime(scheduled_event.get("start_time"), "%Y-%m-%dT%H:%M:%S.%fZ")
            end_dt = datetime.strptime(scheduled_event.get("end_time"), "%Y-%m-%dT%H:%M:%S.%fZ")

            # Format timezone correctly
            start_datetime_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            end_datetime_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

            # Check and add email to CRM
            who_id = check_and_add_email({"email": email, "firstName": first_name, "lastName": last_name}, Module, only_contact=True)

            # Construct event data
            event_data = {
                "Event_Title": f"Meeting: {scheduled_event.get('name')} with {first_name} {last_name}",
                "Subject": f"Meeting: {scheduled_event.get('name')} with {first_name} {last_name}",
                "Start_DateTime": start_datetime_str,
                "End_DateTime": end_datetime_str,
                "Participants": [{"participant": email, "type": "email"}],
                "Location": join_url if join_url else location_type,
                "Description": description,
                "Who_Id": who_id,
                "Calendly_Event_URI": scheduled_event.get("uri"),
                "Calendly_Invitee_URI": payload.get("uri"),
                "Calendly_Cancel_URL": payload.get("cancel_url"),
                "Calendly_Reschedule_URL": payload.get("reschedule_url"),
                "Timezone": payload.get("timezone"),
            }

            print(event_data)

            if event_type == "invitee.created":
                print("Creating new appointment in Zoho CRM...")
                appointment_data_created = add_meeting_to_zoho_crm(event_data, app_user_id)

            elif event_type == "invitee.canceled":
                print("Canceling appointment in Zoho CRM...")
                appointment_data_created = delete_meeting_from_zoho_crm(scheduled_event.get("uri"), app_user_id)

            elif event_type == "invitee.rescheduled":
                print("Rescheduling appointment in Zoho CRM...")
                appointment_data_created = update_meeting_in_zoho_crm(event_data, app_user_id)

            if appointment_data_created:
                return JsonResponse({
                    "message": f"Appointment {event_type.replace('invitee.', '')} successfully.",
                    "event_data": event_data,
                })
            else:
                return JsonResponse(
                    {"message": f"Failed to {event_type.replace('invitee.', '')} appointment."}, 
                    status=500
                )

        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON payload."}, status=400)
        except Exception as e:
            logger.error(f"Error while handling the webhook: {e}")
            return JsonResponse({"message": f"Internal server error: {str(e)}"}, status=500)

    return HttpResponseBadRequest("Invalid request method.")

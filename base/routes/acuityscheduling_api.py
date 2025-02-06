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
        logger.error("Acuity credentials not found for the user.")
        return None
    except Exception as e:
        logger.error(f"Error while fetching appointment details: {e}")
        return None


@csrf_exempt
def acuity_webhook_create_meeting(request, credential_id, user_id):
    """
    View to handle incoming webhooks from Acuity Scheduling.
    Supports both scheduled and rescheduled appointments.
    """
    Module = "Contacts"
    app_user_id = user_id
    
    if request.method == "POST":
        try:
            # Parse form-encoded data
            data = request.POST
            action = data.get("action")  # 'appointment.scheduled' or 'appointment.rescheduled'
            appointment_id = data.get("id")

            if not action or not appointment_id:
                return JsonResponse({"message": "Missing required data in the webhook payload."}, status=400)

            # Fetch updated appointment details
            appointment_data = get_appointment_details(credential_id, appointment_id)
            appointment_data["app_user_id"] = user_id  # Store user ID in the appointment data
            
            try:
                settings = Settings.objects.get(user_id=user_id) 
                Module = settings.leads_to_store   
            except Exception as e:
                Module = "Contacts"
                
            print(f"Search the data in CRM of {Module}")

            user_id = check_and_add_email(appointment_data, Module)
            candidate_name = f"{appointment_data.get('firstName', '')} {appointment_data.get('lastName', '')}"
            
            # Convert datetime string to datetime object
            start_dt = datetime.strptime(appointment_data.get("datetime"), "%Y-%m-%dT%H:%M:%S%z")
            end_dt = start_dt + timedelta(minutes=int(appointment_data.get("duration")))

            # Format timezone correctly
            start_datetime_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S") + start_dt.strftime("%z")[:3] + ":" + start_dt.strftime("%z")[3:]
            end_datetime_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S") + end_dt.strftime("%z")[:3] + ":" + end_dt.strftime("%z")[3:]

            who_id = check_and_add_email(appointment_data, Module, only_contact=True)

            # Construct event data
            event_data = {
                "Event_Title": f"Meeting: {appointment_data.get('type')} with {candidate_name}",
                "Subject": f"Meeting: {appointment_data.get('type')} with {candidate_name}",
                "Start_DateTime": start_datetime_str,  
                "End_DateTime": end_datetime_str,      
                "Participants": [{"participant": str(appointment_data.get("email")), "type": "email"}],
                "Location": str(appointment_data.get("location")),
                "Description": str(appointment_data.get("formsText")),
                "Who_Id": who_id,
                "Acuity_Client_Link": str(appointment_data.get("confirmationPage")),
                "Acuity_ID": str(appointment_data.get("id")),
                "Acuity_Agent_Link": "https://secure.acuityscheduling.com/appointments/view/" + str(appointment_data.get("id")),
                "Acuity_Calendar_Name": str(appointment_data.get("calendar")),
                "Acuity_Calendar_Email": str(appointment_data.get("email")),
                "Acuity_Event_Price": str(appointment_data.get("price")),
            }

            print(event_data)

            if action == "appointment.scheduled":
                print("Creating new appointment in Zoho CRM...")
                appointment_data_created = add_meeting_to_zoho_crm(event_data, app_user_id)

            elif action == "appointment.rescheduled":
                print("Rescheduling appointment in Zoho CRM...")
                appointment_data_created = update_meeting_in_zoho_crm(event_data, app_user_id)
                
            elif action == "appointment.canceled":
                print("Canceling appointment in Zoho CRM...")
                appointment_data_created = delete_meeting_from_zoho_crm(appointment_data["id"], app_user_id)

            if appointment_data_created:
                return JsonResponse(
                    {
                        "message": f"Appointment {action.replace('appointment.', '')} successfully.",
                        "appointment_data": appointment_data,
                    }
                )
            else:
                return JsonResponse(
                    {"message": f"Failed to {action.replace('appointment.', '')} appointment."}, status=500
                )

        except Exception as e:
            logger.error(f"Error while handling the webhook: {e}")
            return JsonResponse({"message": "Internal server error."}, status=500)

    return HttpResponseBadRequest("Invalid request method.")

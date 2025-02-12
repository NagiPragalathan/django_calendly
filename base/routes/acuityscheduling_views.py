from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from Finalty.settings import ACUITY_WEBHOOK_EVENTS, ACUITY_CUSTOM_FIELDS
from base.models import CalendlyCredentials
import requests, json
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta, timezone
from django.core.paginator import Paginator
from django.utils.html import escape
from django.db.models import Q
from datetime import datetime
from django.utils.dateparse import parse_datetime
from requests.auth import HTTPBasicAuth
from base.routes.tool_kit.acuityscheduling_tool import create_webhooks
from base.routes.tool_kit.secract_del import delete_all_webhooks
from base.routes.tool_kit.mongo_tool import store_image_in_mongodb, get_image_from_mongodb
from base.routes.tool_kit.zoho_tool import ensure_field_exists
import base64
from django.conf import settings

@login_required
def list_appointments(request):
    email = request.user.email

    try:
        # Get credentials
        credentials = CalendlyCredentials.objects.filter(email=email).first()
        if not credentials:
            return render(request, 'acuityscheduling/appointments.html', {
                'error': 'No Calendly Credentials found for your account. '
                         '<a href="/store-credentials/" class="text-blue-600 underline">Store credentials</a>'
            })

        # Check if access token is expired and refresh if needed
        headers = check_and_refresh_token(credentials)
        if not headers:
            return render(request, 'acuityscheduling/appointments.html', {
                'error': 'Failed to authenticate with Calendly. Please try storing your credentials again.'
            })

        # Get user's information and organization
        user_url = 'https://api.calendly.com/users/me'
        user_response = requests.get(user_url, headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        organization_uri = user_data['resource']['current_organization']

        # Get upcoming appointments for next 30 days
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=30)

        # Format dates for Calendly API
        start_date = now.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
        end_date = end_date.strftime('%Y-%m-%dT%H:%M:%S.000000Z')

        # Make API request to Calendly
        url = 'https://api.calendly.com/scheduled_events'
        params = {
            'min_start_time': start_date,
            'max_start_time': end_date,
            'organization': organization_uri,
            'status': 'active',
            'count': 100,
            'sort': 'start_time:asc'  # Sort by start time ascending for upcoming events
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        appointments = []

        # Get event types for service filtering
        event_types_url = 'https://api.calendly.com/event_types'
        event_types_response = requests.get(
            event_types_url,
            headers=headers,
            params={'organization': organization_uri}
        )
        event_types_data = event_types_response.json()
        service_types = sorted({et['name'] for et in event_types_data.get('collection', [])})

        # Process appointments
        for event in data.get('collection', []):
            event_start = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['end_time'].replace('Z', '+00:00'))
            
            # Get invitee details
            invitee_response = requests.get(
                f"{event['uri']}/invitees",
                headers=headers
            ).json()
            
            invitees = invitee_response.get('collection', [{}])
            for invitee in invitees:
                try:
                    appointment = {
                        # Basic Info
                        'firstName': invitee.get('first_name', ''),
                        'lastName': invitee.get('last_name', ''),
                        'email': invitee.get('email', ''),
                        
                        # Time Information
                        'datetime': event['start_time'],
                        'date': event_start.date(),
                        'time': event_start.time(),
                        'endTime': event_end.time(),
                        'created_at': event.get('created_at'),
                        'updated_at': event.get('updated_at'),
                        
                        # Event Details
                        'event_uri': event['uri'],
                        'name': event.get('name', ''),
                        'type': event.get('name', ''),
                        'status': event.get('status', ''),
                        'meeting_notes_plain': event.get('meeting_notes_plain', ''),
                        'meeting_notes_html': event.get('meeting_notes_html', ''),
                        
                        # Location
                        'location_type': event.get('location', {}).get('type', ''),
                        'location_address': event.get('location', {}).get('location', ''),
                        'location_info': event.get('location', {}).get('additional_info', ''),
                        
                        # URLs
                        'cancel_url': invitee.get('cancel_url', ''),
                        'reschedule_url': invitee.get('reschedule_url', ''),
                        'scheduling_url': invitee.get('scheduling_url', ''),
                        
                        # Counter Information
                        'invitees_total': event.get('invitees_counter', {}).get('total', 0),
                        'invitees_active': event.get('invitees_counter', {}).get('active', 0),
                        'invitees_limit': event.get('invitees_counter', {}).get('limit', 0),
                        
                        # Event Members
                        'event_members': [{
                            'name': member.get('user_name', ''),
                            'email': member.get('user_email', ''),
                            'buffered_start': member.get('buffered_start_time', ''),
                            'buffered_end': member.get('buffered_end_time', '')
                        } for member in event.get('event_memberships', [])],
                        
                        # Event Guests
                        'event_guests': [{
                            'email': guest.get('email', ''),
                            'created_at': guest.get('created_at', ''),
                            'updated_at': guest.get('updated_at', '')
                        } for guest in event.get('event_guests', [])]
                    }
                    appointments.append(appointment)
                except (ValueError, KeyError) as e:
                    print(f"Error processing appointment: {str(e)}")
                    continue

        # Pagination
        paginator = Paginator(appointments, 10)  # Show 10 appointments per page
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        return render(request, 'acuityscheduling/appointments.html', {
            'page_obj': page_obj,
            'request': request,
            'service_types': service_types,
            'start_date': start_date,
            'end_date': end_date
        })

    except requests.exceptions.RequestException as e:
        return render(request, 'acuityscheduling/appointments.html', {
            'error': f"Failed to fetch appointments. Please try again later.<br>Error: {str(e)}"
        })

def check_and_refresh_token(credentials):
    """Helper function to check token expiration and refresh if needed"""
    try:
        # Try to decode the access token to check expiration
        token_parts = credentials.access_token.split('.')
        if len(token_parts) != 3:
            raise ValueError("Invalid token format")
            
        # Decode the payload
        payload = json.loads(base64.b64decode(token_parts[1] + '=' * (-len(token_parts[1]) % 4)).decode('utf-8'))
        
        # Check if token is expired
        exp_timestamp = payload.get('exp')
        if not exp_timestamp:
            raise ValueError("No expiration time in token")
            
        if datetime.fromtimestamp(exp_timestamp) <= datetime.now():
            # Token is expired, refresh it
            refresh_url = 'https://auth.calendly.com/oauth/token'
            refresh_data = {
                'client_id': settings.CALENDLY_CLIENT_ID,
                'client_secret': settings.CALENDLY_CLIENT_SECRET,
                'grant_type': 'refresh_token',
                'refresh_token': credentials.refresh_token
            }
            
            response = requests.post(refresh_url, data=refresh_data)
            response.raise_for_status()
            
            token_data = response.json()
            
            CalendlyCredentials.objects.filter(unique_id=credentials.unique_id).update(
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token']
            )
            
        # Return headers for API requests
        return {
            'Authorization': f'Bearer {credentials.access_token}',
            'Content-Type': 'application/json'
        }
        
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        return None


@login_required
def past_appointments(request):
    email = request.user.email

    try:
        # Get credentials
        credentials = CalendlyCredentials.objects.filter(email=email).first()
        if not credentials:
            return render(request, 'acuityscheduling/past_appointments.html', {
                'error': 'No Calendly Credentials found for your account. '
                         '<a href="/store-credentials/" class="text-blue-600 underline">Store credentials</a>'
            })

        # Check if access token is expired and refresh if needed
        headers = check_and_refresh_token(credentials)
        if not headers:
            return render(request, 'acuityscheduling/past_appointments.html', {
                'error': 'Failed to authenticate with Calendly. Please try storing your credentials again.'
            })

        # Get user's information and organization
        user_url = 'https://api.calendly.com/users/me'
        user_response = requests.get(user_url, headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        organization_uri = user_data['resource']['current_organization']

        # Set up date parameters
        now = datetime.now(timezone.utc)
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Default to past 30 days if no dates specified
        if not end_date:
            end_date = now
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            
        if not start_date:
            start_date = now - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)

        # Format dates properly for Calendly API
        min_start_time = start_date.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
        max_start_time = end_date.strftime('%Y-%m-%dT%H:%M:%S.000000Z')

        # Make API request to Calendly
        url = 'https://api.calendly.com/scheduled_events'
        params = {
            'min_start_time': min_start_time,
            'max_start_time': max_start_time,
            'organization': organization_uri,
            'status': 'active',
            'count': 100,
            'sort': 'start_time:desc'
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        appointments = []

        # Get event types for service filtering
        event_types_url = 'https://api.calendly.com/event_types'
        event_types_response = requests.get(
            event_types_url,
            headers=headers,
            params={'organization': organization_uri}
        )
        event_types_data = event_types_response.json()
        
        # Fix: Correctly access the event type names
        service_types = set()
        for event_type in event_types_data.get('collection', []):
            if 'name' in event_type:  # Direct access to name
                service_types.add(event_type['name'])
        service_types = sorted(service_types)

        # Process appointments
        for event in data.get('collection', []):
            # Get event details and memberships
            event_memberships = event.get('event_memberships', [])
            event_guests = event.get('event_guests', [])
            
            # Get invitee details
            invitee_response = requests.get(
                f"{event['uri']}/invitees",
                headers=headers
            ).json()
            
            invitees = invitee_response.get('collection', [{}])
            for invitee in invitees:
                try:
                    event_start = datetime.strptime(event['start_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    event_end = datetime.strptime(event['end_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    
                    # Create a more detailed appointment dictionary
                    appointment = {
                        # Basic Info
                        'firstName': invitee.get('first_name', ''),
                        'lastName': invitee.get('last_name', ''),
                        'email': invitee.get('email', ''),
                        
                        # Time Information
                        'datetime': event['start_time'],
                        'date': event_start.date(),
                        'time': event_start.time(),
                        'endTime': event_end.time(),
                        'created_at': event.get('created_at'),
                        'updated_at': event.get('updated_at'),
                        
                        # Event Details
                        'event_uri': event['uri'],
                        'name': event.get('name', ''),
                        'type': event.get('name', ''),
                        'status': event.get('status', ''),
                        'meeting_notes_plain': event.get('meeting_notes_plain', ''),
                        'meeting_notes_html': event.get('meeting_notes_html', ''),
                        
                        # Location
                        'location_type': event.get('location', {}).get('type', ''),
                        'location_address': event.get('location', {}).get('location', ''),
                        'location_info': event.get('location', {}).get('additional_info', ''),
                        
                        # URLs
                        'cancel_url': invitee.get('cancel_url', ''),
                        'reschedule_url': invitee.get('reschedule_url', ''),
                        'scheduling_url': invitee.get('scheduling_url', ''),
                        
                        # Counter Information
                        'invitees_total': event.get('invitees_counter', {}).get('total', 0),
                        'invitees_active': event.get('invitees_counter', {}).get('active', 0),
                        'invitees_limit': event.get('invitees_counter', {}).get('limit', 0),
                        
                        # Event Members
                        'event_members': [{
                            'name': member.get('user_name', ''),
                            'email': member.get('user_email', ''),
                            'buffered_start': member.get('buffered_start_time', ''),
                            'buffered_end': member.get('buffered_end_time', '')
                        } for member in event_memberships],
                        
                        # Event Guests
                        'event_guests': [{
                            'email': guest.get('email', ''),
                            'created_at': guest.get('created_at', ''),
                            'updated_at': guest.get('updated_at', '')
                        } for guest in event_guests],
                        
                        # Calendar Information
                        'calendar_type': event.get('calendar_event', {}).get('kind', ''),
                        'calendar_id': event.get('calendar_event', {}).get('external_id', '')
                    }
                    appointments.append(appointment)
                except (ValueError, KeyError) as e:
                    print(f"Error processing appointment: {str(e)}")
                    continue

        # Apply filters
        query = request.GET.get('q', '').strip()
        start_time = request.GET.get('start_time')
        end_time = request.GET.get('end_time')
        service_type = request.GET.get('service_type')

        if query:
            appointments = [
                appt for appt in appointments
                if query.lower() in f"{appt['firstName']} {appt['lastName']} {appt['type']}".lower()
            ]

        if start_time:
            start_time_dt = datetime.strptime(start_time, '%H:%M').time()
            appointments = [appt for appt in appointments if appt['time'] >= start_time_dt]
            
        if end_time:
            end_time_dt = datetime.strptime(end_time, '%H:%M').time()
            appointments = [appt for appt in appointments if appt['time'] <= end_time_dt]

        if service_type:
            appointments = [appt for appt in appointments if appt['type'] == service_type]

        # Pagination
        paginator = Paginator(appointments, 21)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        return render(request, 'acuityscheduling/past_appointments.html', {
            'page_obj': page_obj,
            'request': request,
            'service_types': service_types
        })

    except requests.exceptions.RequestException as e:
        return render(request, 'acuityscheduling/past_appointments.html', {
            'error': f"Failed to fetch appointments. Please try again later.<br>Error: {str(e)}"
        })


def appointment_types_view(request):
    """
    Fetch and display appointment types with links.
    """
    email = request.user.email

    try:
        credentials = CalendlyCredentials.objects.get(email=email)
    except CalendlyCredentials.DoesNotExist:
        return render(request, 'acuityscheduling/appointments.html', {
            'error': 'No Calendly Credentials found for your account. '
                     '<a href="/store-credentials/" class="text-blue-600 underline">Store credentials</a>'
        })

    user_id = credentials.user_id
    api_key = credentials.api_key
    base_url = "https://acuityscheduling.com/api/v1"
    appointment_types_endpoint = f"{base_url}/appointment-types"
    auth = HTTPBasicAuth(user_id, api_key)

    try:
        response = requests.get(appointment_types_endpoint, auth=auth)
        response.raise_for_status()
        appointment_types = response.json()

        # Add links and color tags
        for appt_type in appointment_types:
            appt_type["link"] = f"https://app.acuityscheduling.com/schedule.php?owner={user_id}&appointmentType={appt_type.get('id')}"

        # Get unique colors for filter
        unique_colors = list(set(appt_type["color"] for appt_type in appointment_types if appt_type["color"]))

        # Filter by color if specified
        selected_color = request.GET.get("color")
        if selected_color:
            appointment_types = [appt for appt in appointment_types if appt["color"] == selected_color]

        return render(request, 'acuityscheduling/appointment_types.html', {
            'appointment_types': appointment_types,
            'colors': unique_colors,
        })

    except requests.RequestException as e:
        return render(request, 'acuityscheduling/appointment_types.html', {'error': f"Failed to fetch appointment types: {str(e)}"})


def acuity_dashboard(request):
    """
    Fetch and display data for Acuity Scheduling Dashboard.
    """
    email = request.user.email

    try:
        credentials = CalendlyCredentials.objects.get(email=email)
    except CalendlyCredentials.DoesNotExist:
        return render(request, 'acuityscheduling/dashboard.html', {
            'error': 'No Calendly Credentials found for your account. Store credentials by clicking &nbsp;&nbsp;'
                     '<a href="/store-credentials/" class="text-blue-600 underline">here</a>'
        })

    USER_ID = credentials.user_id
    API_KEY = credentials.api_key
    base_url = "https://acuityscheduling.com/api/v1"
    auth = HTTPBasicAuth(USER_ID, API_KEY)

    # Endpoints
    appointment_types_endpoint = f"{base_url}/appointment-types"
    past_appointments_endpoint = f"{base_url}/appointments"

    service_types = []
    past_appointments = []
    total_revenue = 0

    try:
        # Fetch service types
        response = requests.get(appointment_types_endpoint, auth=auth)
        response.raise_for_status()
        service_types = response.json()

        # Fetch past appointments
        params = {'maxDate': '2024-11-26', 'direction': 'DESC'}
        response = requests.get(past_appointments_endpoint, auth=auth, params=params)
        response.raise_for_status()
        past_appointments = response.json()

        # Calculate total revenue from service types
        total_revenue = sum(float(service.get("price", 0)) for service in service_types)

        # Process data for visualizations
        service_price_data = [
            {"name": service["name"], "price": float(service.get("price", 0))} for service in service_types
        ]
        appointment_status_data = {
            "completed": sum(1 for appt in past_appointments if appt.get("status") == "completed"),
            "upcoming": sum(1 for appt in past_appointments if appt.get("status") == "upcoming"),
            "cancelled": sum(1 for appt in past_appointments if appt.get("status") == "cancelled"),
        }

        # Process appointment history data
        sorted_dates = sorted(set(appt['date'] for appt in past_appointments))
        appointment_history = [sum(1 for appt in past_appointments if appt['date'] == date) for date in sorted_dates]

        # Process clients data
        clients = [{"firstName": appt.get("firstName"), "lastName": appt.get("lastName"), "email": appt.get("email")} for appt in past_appointments]

        # Pass all processed data to the template
        context = {
            "service_types": service_types,
            "past_appointments": past_appointments,
            "total_revenue": total_revenue,
            "service_price_data": service_price_data,
            "appointment_status_data": appointment_status_data,
            "appointment_history": appointment_history,
            "sorted_dates": sorted_dates,
            "clients": clients,
        }

        return render(request, 'acuityscheduling/dashboard.html', context)

    except requests.RequestException as e:
        return render(request, 'acuityscheduling/dashboard.html', {'error': f"Failed to fetch data: {str(e)}"})


def reset_webhook_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        api_key = request.POST.get('api_key')
        if user_id and api_key:
            try:
                print(f"User ID: {user_id}, API Key: {api_key}")
                delete_all_webhooks(user_id, api_key)
                # Simulate webhook reset logic
                return JsonResponse({'success': True, 'message': 'Webhook reset successful.'})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        else:
            return JsonResponse({'error': 'Missing user_id or api_key'}, status=400)
    return render(request, 'acuityscheduling/reset_webhook.html')

def acuity_schedule(request):
    email = request.user.email
    print(request.image_url)
    try:
        credentials = CalendlyCredentials.objects.get(email=email)
    except CalendlyCredentials.DoesNotExist:
        return render(request, 'acuityscheduling/acuity_schedule.html', {
            'error': 'No Calendly Credentials found for your account. Store credentials by clicking &nbsp;&nbsp;'
                     '<a href="/store-credentials/" class="text-blue-600 underline">here</a>'
        })
    return render(request, 'acuityscheduling/acuity_schedule.html', {'embedCode': credentials.embedCode})


def serve_image(request, image_id):
    """
    Serve the image stored in MongoDB by its ID.
    :param image_id: The ID of the image in MongoDB.
    :return: An HTTP response containing the image content.
    """
    try:
        # Retrieve the image content
        image_content = get_image_from_mongodb(image_id)

        # Serve the image as a response
        return HttpResponse(image_content, content_type="image/jpeg")
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
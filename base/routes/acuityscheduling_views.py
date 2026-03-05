
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from Finalty.settings import CALENDLY_WEBHOOK_EVENTS, CALENDLY_CUSTOM_FIELDS
from base.models import CalendlyCredentials, ZohoToken, Settings, PreFillMapping, SmtpSettings, BookingEmailTemplate
from base.routes.tool_kit.zoho_tool import add_meeting_to_zoho_crm, check_and_add_email, get_zoho_record
from django.core.mail import EmailMessage, get_connection
import requests, json
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta, timezone
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from base.utils import get_active_hub
from base.routes.tool_kit.secract_del import delete_all_webhooks
from base.routes.tool_kit.mongo_tool import get_image_from_mongodb
import base64
from django.conf import settings
from django.utils.safestring import mark_safe


@login_required
def list_appointments(request):
    email = request.user.email
    search_query = request.GET.get('search', '').strip()
    start_date_val = request.GET.get('start_date', '')
    end_date_val = request.GET.get('end_date', '')

    try:
        credentials = get_active_hub(request)
        if not credentials:
            return render(request, 'acuityscheduling/appointments.html', {
                'error': mark_safe('No Calendly Credentials found for your account. '
                          '<a href="/credentials/create/" class="text-blue-600 underline">Add credentials hub</a>')
            })

        # Check if access token is expired and refresh if needed
        headers = check_and_refresh_token(credentials)
        if not headers:
            return render(request, 'acuityscheduling/appointments.html', {
                'error': 'Failed to authenticate with Calendly. Please try storing your credentials again.'
            })

        # Get user's information using the correct API endpoint
        user_url = 'https://api.calendly.com/users/me'
        user_response = requests.get(user_url, headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        
        # Get organization URI from user data
        organization_uri = user_data.get('resource', {}).get('current_organization')
        user_uri = user_data.get('resource', {}).get('uri')

        # Calculate time range
        now = datetime.now(timezone.utc)
        if start_date_val:
            try:
                min_time = datetime.strptime(start_date_val, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                min_time = now
        else:
            min_time = now

        if end_date_val:
            try:
                max_time = datetime.strptime(end_date_val, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            except ValueError:
                max_time = min_time + timedelta(days=30)
        else:
            max_time = min_time + timedelta(days=30)
        
        events_url = 'https://api.calendly.com/scheduled_events'
        events_params = {
            'organization': organization_uri,
            'min_start_time': min_time.isoformat(),
            'max_start_time': max_time.isoformat(),
            'user': user_uri,
            'status': 'active',
            'count': 100
        }

        # If search looks like an email, we can use Calendly's built-in filter
        if "@" in search_query:
            events_params['invitee_email'] = search_query

        events_response = requests.get(events_url, headers=headers, params=events_params)
        events_response.raise_for_status()
        events_data = events_response.json()
        scheduled_events = events_data.get('collection', [])

        # Get event types for sharing
        event_types_url = 'https://api.calendly.com/event_types'
        event_types_response = requests.get(
            event_types_url,
            headers=headers,
            params={'organization': organization_uri, 'user': user_uri, 'active': True}
        )
        event_types_data = event_types_response.json()
        all_event_types = []
        for et in event_types_data.get('collection', []):
            all_event_types.append({
                'name': et['name'],
                'duration': et['duration'],
                'color': et.get('color', '#6366f1'),
                'kind': et.get('kind', 'Standard'),
                'scheduling_url': et['scheduling_url']
            })
        service_types = sorted({et['name'] for et in all_event_types})

        # Process appointments
        appointments = []
        for event in scheduled_events:
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
                    # Filter by search query if not already filtered by email in API
                    if search_query and "@" not in search_query:
                        search_lower = search_query.lower()
                        match = (
                            search_lower in invitee.get('name', '').lower() or
                            search_lower in invitee.get('email', '').lower() or
                            search_lower in event.get('name', '').lower()
                        )
                        if not match:
                            continue

                    appointment = {
                        # Basic Info
                        'firstName': invitee.get('first_name', '') or invitee.get('name', '').split(' ')[0],
                        'lastName': invitee.get('last_name', '') or ' '.join(invitee.get('name', '').split(' ')[1:]),
                        'email': invitee.get('email', ''),
                        
                        # Time Information
                        'datetime': event['start_time'],
                        'date': event_start.date(),
                        'time': event_start.time(),
                        'start_time': event_start, # For template formatting
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
                        'location_type': (event.get('location') or {}).get('type', ''),
                        'location_address': (event.get('location') or {}).get('location', ''),
                        'location_info': (event.get('location') or {}).get('additional_info', ''),
                        
                        # URLs
                        'cancel_url': invitee.get('cancel_url', ''),
                        'reschedule_url': invitee.get('reschedule_url', ''),
                        'scheduling_url': invitee.get('scheduling_url', ''),
                        
                        # Counter Information
                        'invitees_total': (event.get('invitees_counter') or {}).get('total', 0),
                        'invitees_active': (event.get('invitees_counter') or {}).get('active', 0),
                        'invitees_limit': (event.get('invitees_counter') or {}).get('limit', 0),
                        
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
                    # Add full JSON data for the popup
                    appointment['full_data_json'] = json.dumps(appointment, default=str)
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
            'all_event_types': all_event_types,
            'min_time': min_time,
            'max_time': max_time,
            'start_date': min_time.isoformat(),
            'end_date': max_time.isoformat(),
            'search_query': search_query,
            'start_date_val': start_date_val,
            'end_date_val': end_date_val
        })

    except Exception as e:
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
            
        if datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) <= datetime.now(timezone.utc):
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
            
            # Update the Python object so the returned headers have the new token
            credentials.access_token = token_data['access_token']
            credentials.refresh_token = token_data['refresh_token']
            
            CalendlyCredentials.objects.filter(unique_id=credentials.unique_id).update(
                access_token=credentials.access_token,
                refresh_token=credentials.refresh_token
            )
            
        # Return headers with the updated token
        return {
            'Authorization': f'Bearer {credentials.access_token}',
            'Content-Type': 'application/json'
        }
        
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        # Return empty dict instead of None to prevent 'items' attribute errors in templates or requests
        return {
            'Authorization': f'Bearer {credentials.access_token}',
            'Content-Type': 'application/json'
        }


@login_required
def past_appointments(request):
    email = request.user.email

    try:
        # Get active hub (session, primary, or first available)
        credentials = get_active_hub(request)
        if not credentials:
            return render(request, 'acuityscheduling/past_appointments.html', {
                'error': mark_safe('No Calendly Credentials found for your account. '
                          '<a href="/credentials/create/" class="text-blue-600 underline">Add credentials hub</a>')
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
                        'location_type': (event.get('location') or {}).get('type', ''),
                        'location_address': (event.get('location') or {}).get('location', ''),
                        'location_info': (event.get('location') or {}).get('additional_info', ''),
                        
                        # URLs
                        'cancel_url': invitee.get('cancel_url', ''),
                        'reschedule_url': invitee.get('reschedule_url', ''),
                        'scheduling_url': invitee.get('scheduling_url', ''),
                        
                        # Counter Information
                        'invitees_total': (event.get('invitees_counter') or {}).get('total', 0),
                        'invitees_active': (event.get('invitees_counter') or {}).get('active', 0),
                        'invitees_limit': (event.get('invitees_counter') or {}).get('limit', 0),
                        
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
                        'calendar_type': (event.get('calendar_event') or {}).get('kind', ''),
                        'calendar_id': (event.get('calendar_event') or {}).get('external_id', '')
                    }
                    # Add full JSON data for the popup
                    appointment['full_data_json'] = json.dumps(appointment, default=str)
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
        return render(request, 'acuityscheduling/appointment_types.html', {
            'error': 'No Calendly Credentials found for your account. '
                     '<a href="/store-credentials/" class="text-blue-600 underline">Store credentials</a>'
        })

    # Check and refresh token if needed
    headers = check_and_refresh_token(credentials)
    if not headers:
        return render(request, 'acuityscheduling/appointment_types.html', {
            'error': 'Failed to authenticate with Calendly. Please reconnect your account.'
        })

    try:
        # Get user info first
        user_response = requests.get('https://api.calendly.com/users/me', headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        organization_uri = user_data['resource']['current_organization']
        user_uri = user_data['resource']['uri']

        # Get event types
        event_types_url = 'https://api.calendly.com/event_types'
        params = {
            'organization': organization_uri,
            'user': user_uri,
            'active': True
        }
        
        response = requests.get(event_types_url, headers=headers, params=params)
        response.raise_for_status()
        event_types = response.json().get('collection', [])

        # Process event types and create single-use links
        appointment_types = []
        for event in event_types:
            # Create single-use scheduling link
            scheduling_link_data = {
                "max_event_count": 1,
                "owner": event['uri'],
                "owner_type": "EventType"
            }
            
            try:
                link_response = requests.post(
                    'https://api.calendly.com/scheduling_links',
                    headers=headers,
                    json=scheduling_link_data
                )
                link_response.raise_for_status()
                single_use_link = link_response.json()['resource']['booking_url']
            except:
                single_use_link = event['scheduling_url']  # Fallback to regular link

            appointment_types.append({
                'name': event['name'],
                'description': event.get('description', ''),
                'duration': event['duration'],
                'color': event.get('color', '#3B82F6'),
                'scheduling_url': event['scheduling_url'],
                'single_use_url': single_use_link,
                'type': event['type'],
                'slug': event['slug'],
                'active': event.get('active', True),
                'full_data_json': json.dumps(event, default=str)
            })

        return render(request, 'acuityscheduling/appointment_types.html', {
            'appointment_types': appointment_types,
            'user_name': user_data['resource'].get('name', '')
        })

    except requests.RequestException as e:
        return render(request, 'acuityscheduling/appointment_types.html', 
                     {'error': f"Failed to fetch appointment types: {str(e)}"})


@login_required
def send_booking_email(request):
    """Send an orchestrated booking email via SMTP."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
        
    try:
        to_email = request.POST.get('to_email')
        subject = request.POST.get('subject', 'Invitation to Schedule a Meeting')
        message_content = request.POST.get('message_content')
        booking_url = request.POST.get('booking_url')
        
        # 1. Get SMTP Settings
        smtp = SmtpSettings.objects.filter(user=request.user).first()
        if not smtp:
            return JsonResponse({'success': False, 'error': 'SMTP settings not configured. Please set them in Integration Settings.'}, status=400)
            
        # 2. Add Booking Link to Message
        full_message = f"{message_content}\n\nSchedule here: {booking_url}"
        
        # 3. Create Connection
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=smtp.smtp_server,
            port=smtp.smtp_port,
            username=smtp.smtp_user,
            password=smtp.smtp_password,
            use_tls=smtp.use_tls,
            timeout=10
        )
        
        # 4. Send Email
        email = EmailMessage(
            subject=subject,
            body=full_message,
            from_email=smtp.smtp_user,
            to=[to_email],
            connection=connection
        )
        email.send()
        
        return JsonResponse({'success': True, 'message': f'Booking invitation sent to {to_email}!'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Failed to send email: {str(e)}"}, status=500)

@login_required
def zoho_record_booking(request, module, record_id):
    """
    Advanced Orchestrator for Zoho Records.
    Provides a full-screen interface to select event types and email templates.
    """
    try:
        # 1. Fetch Record Intelligence from Zoho
        zoho_token = ZohoToken.objects.filter(user=request.user).order_by('-created_at').first()
        if not zoho_token:
            return render(request, 'zoho/auth_page.html', {
                'error': 'Zoho CRM Bridge not initialized. Please connect your account.',
                'zoho_url': f"https://accounts.zoho.com/oauth/v2/auth?scope=ZohoCRM.modules.ALL,ZohoCRM.users.ALL,ZohoCRM.settings.ALL,ZohoCRM.org.ALL&client_id={settings.CLIENT_ID}&response_type=code&access_type=offline&prompt=consent&redirect_uri={settings.REDIRECT_URI}"
            })
            
        from base.routes.tool_kit.zoho_tool import check_access_token_validity, get_access_token
        # from Finalty.settings import CLIENT_ID, CLIENT_SECRET # Removed as we use from django.conf import settings
        
        access_token = zoho_token.access_token
        if not check_access_token_validity(access_token):
            access_token = get_access_token(settings.CLIENT_ID, settings.CLIENT_SECRET, zoho_token.refresh_token)
            zoho_token.access_token = access_token
            zoho_token.save()
            
        record = get_zoho_record(module, record_id, access_token)
        if not record:
            return HttpResponse(f"Record {record_id} not found in {module}", status=404)

        email = record.get('Email')
        name = record.get('Full_Name') or f"{record.get('First_Name', '')} {record.get('Last_Name', '')}".strip()

        # 2. Identify Hub context
        credentials = get_active_hub(request)
        if not credentials:
            return redirect('list_credentials')
        
        headers = check_and_refresh_token(credentials)
        user_response = requests.get('https://api.calendly.com/users/me', headers=headers)
        
        if user_response.status_code != 200:
            messages.error(request, "Failed to authenticate with Calendly. Please reconnect your account.")
            return redirect('list_credentials')
            
        user_data = user_response.json().get('resource', {})
        if not user_data:
             messages.error(request, "Could not retrieve Calendly user profile.")
             return redirect('list_credentials')
             
        organization_uri = user_data.get('current_organization')

        # 3. Fetch History (Upcoming & Past) for this Invitee
        now = datetime.now(timezone.utc)
        
        # Calendly API v2 supports invitee_email filtering
        events_base_url = 'https://api.calendly.com/scheduled_events'
        
        upcoming_params = {
            'organization': organization_uri,
            'invitee_email': email,
            'min_start_time': now.isoformat(),
            'status': 'active'
        }
        upcoming_res = requests.get(events_base_url, headers=headers, params=upcoming_params)
        upcoming = upcoming_res.json().get('collection', []) if upcoming_res.status_code == 200 else []

        past_params = {
            'organization': organization_uri,
            'invitee_email': email,
            'max_start_time': now.isoformat(),
            'status': 'active'
        }
        past_res = requests.get(events_base_url, headers=headers, params=past_params)
        past = past_res.json().get('collection', []) if past_res.status_code == 200 else []

        # 4. Fetch Event Types & Templates
        et_res = requests.get('https://api.calendly.com/event_types', headers=headers, params={'organization': organization_uri, 'active': True})
        event_types = et_res.json().get('collection', []) if et_res.status_code == 200 else []
        
        templates = list(BookingEmailTemplate.objects.filter(credential=credentials))
        if not templates:
            # Provide a high-fidelity default template if none exist
            templates = [{
                'id': 'default',
                'template_name': 'Standard Outreach (Default)',
                'subject': 'Schedule your meeting with [[name]]',
                'body': 'Hi [[name]],\n\nI would like to invite you to schedule a meeting at your earliest convenience.\n\nYou can pick a time that works best for you here: [[link]]\n\nLooking forward to connecting!'
            }]

        # 5. Build Pre-fill Data for the Generator (Module-Aware)
        prefill = {'name': name, 'email': email}
        # Fetch mappings for this account
        mappings = PreFillMapping.objects.filter(user=request.user, calendly_account=credentials)
        
        # We only want to show mappings relevant to the current module or common fields
        for mapping in mappings:
            # If the mapping belongs to the current module, or if it's a common field
            # (In Zoho, Email/Phone often share names across Leads/Contacts)
            zoho_val = record.get(mapping.zoho_field_api_name)
            
            # Key fix: only populate if the field actually exists in this record's module data
            if mapping.zoho_field_api_name in record:
                # If value is null/empty, show a placeholder in the Data Bank for awareness
                prefill[mapping.question_key] = zoho_val if zoho_val not in [None, ''] else '[EMPTY_FIELD]'
            elif mapping.zoho_module == module:
                 # It's our module but field is missing from get_record (unlikely but possible)
                 prefill[mapping.question_key] = '[FIELD_NOT_FOUND]'

        return render(request, 'acuityscheduling/zoho_record_booking.html', {
            'module': module,
            'record_id': record_id,
            'record': record,
            'email': email,
            'name': name,
            'upcoming': upcoming,
            'past': past,
            'event_types': event_types,
            'templates': templates,
            'prefill': prefill,
            'credentials': credentials,
            'no_nav': True  # Full-screen orchestration
        })

    except Exception as e:
        return HttpResponse(f"Orchestration Error: {str(e)}", status=500)


@login_required
def acuity_dashboard(request):
    """
    Fetch and display data for the Calendly Dashboard with advanced analytics.
    """
    credentials = get_active_hub(request)
    if not credentials:
        return render(request, 'acuityscheduling/dashboard.html', {
            'error': mark_safe('No Calendly Credentials found for your account. '
                        '<a href="/credentials/create/" class="text-blue-600 underline">Add credentials hub</a>')
        })

    headers = check_and_refresh_token(credentials)
    if not headers:
        return render(request, 'acuityscheduling/dashboard.html', {
            'error': 'Failed to authenticate with Calendly. Please reconnect your account.'
        })

    try:
        # Get user info
        user_response = requests.get('https://api.calendly.com/users/me', headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()['resource']
        organization_uri = user_data['current_organization']
        user_uri = user_data['uri']

        now = datetime.now(timezone.utc)

        # 1. Today's Events
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        today_params = {
            'organization': organization_uri,
            'min_start_time': start_of_today.isoformat(),
            'max_start_time': end_of_today.isoformat(),
            'status': 'active'
        }
        today_meetings = requests.get('https://api.calendly.com/scheduled_events', headers=headers, params=today_params).json().get('collection', [])

        # 2. Upcoming & Past Meetings (Top 3 each)
        upcoming_params = {
            'organization': organization_uri,
            'min_start_time': now.isoformat(),
            'status': 'active',
            'count': 3,
            'sort': 'start_time:asc'
        }
        upcoming_meetings = requests.get('https://api.calendly.com/scheduled_events', headers=headers, params=upcoming_params).json().get('collection', [])

        past_params = {
            'organization': organization_uri,
            'max_start_time': now.isoformat(),
            'status': 'active',
            'count': 3,
            'sort': 'start_time:desc'
        }
        past_meetings = requests.get('https://api.calendly.com/scheduled_events', headers=headers, params=past_params).json().get('collection', [])

        # 3. Monthly Analytics (Last 30 Days)
        thirty_days_ago = now - timedelta(days=30)
        events_params = {
            'organization': organization_uri,
            'min_start_time': thirty_days_ago.isoformat(),
            'max_start_time': now.isoformat(),
            'count': 100
        }
        scheduled_events = requests.get('https://api.calendly.com/scheduled_events', headers=headers, params=events_params).json().get('collection', [])

        # 4. Event Types Intelligence
        et_response = requests.get('https://api.calendly.com/event_types', headers=headers, params={'organization': organization_uri, 'user': user_uri})
        all_event_types = et_response.json().get('collection', [])
        
        # 5. Recent Activity
        activity_response = requests.get('https://api.calendly.com/activity_log_entries', headers=headers, params={'organization': organization_uri, 'count': 5})
        recent_activity = activity_response.json().get('collection', [])

        # Processing Analytics
        event_status_data = {'active': 0, 'canceled': 0}
        events_by_date = {}
        events_by_hour = {str(h): 0 for h in range(24)}
        events_by_type = {}
        total_duration = 0

        for event in scheduled_events:
            status = event['status']
            event_status_data[status] = event_status_data.get(status, 0) + 1
            st = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
            et = datetime.fromisoformat(event['end_time'].replace('Z', '+00:00'))
            
            events_by_date[st.strftime('%Y-%m-%d')] = events_by_date.get(st.strftime('%Y-%m-%d'), 0) + 1
            events_by_hour[str(st.hour)] += 1
            events_by_type[event['name']] = events_by_type.get(event['name'], 0) + 1
            total_duration += int((et - st).total_seconds() / 60)

        # Get Top 3 Event Types based on frequency or just selection
        top_event_types = sorted(all_event_types, key=lambda x: events_by_type.get(x['name'], 0), reverse=True)[:3]

        def process_meeting(e):
            st = datetime.fromisoformat(e['start_time'].replace('Z', '+00:00'))
            et = datetime.fromisoformat(e['end_time'].replace('Z', '+00:00'))
            return {
                'name': e['name'],
                'time': st.strftime('%b %d, %H:%M'),
                'duration': int((et - st).total_seconds() / 60),
                'uri': e['uri']
            }

        context = {
            'user_data': user_data,
            'today_meetings': [process_meeting(m) for m in today_meetings],
            'upcoming_meetings': [process_meeting(m) for m in upcoming_meetings],
            'past_meetings': [process_meeting(m) for m in past_meetings],
            'top_events': top_event_types,
            'all_event_types': all_event_types,
            'stats': [
                {'label': 'Monthly Orchestrations', 'value': len(scheduled_events), 'icon': 'ri-calendar-event-line', 'color': 'indigo'},
                {'label': 'Avg Engagement', 'value': f"{round(total_duration/len(scheduled_events),1) if scheduled_events else 0}m", 'icon': 'ri-time-line', 'color': 'emerald'},
                {'label': 'Active Links', 'value': len([et for et in all_event_types if et['active']]), 'icon': 'ri-links-line', 'color': 'violet'},
                {'label': 'Success Rate', 'value': f"{round((event_status_data['active']/len(scheduled_events))*100,1) if scheduled_events else 0}%", 'icon': 'ri-shield-check-line', 'color': 'amber'}
            ],
            'recent_activity': recent_activity,
            'event_status_data': mark_safe(json.dumps(event_status_data)),
            'events_by_date': mark_safe(json.dumps(events_by_date)),
            'events_by_hour': mark_safe(json.dumps(events_by_hour)),
            'events_by_type': mark_safe(json.dumps(events_by_type))
        }

        return render(request, 'acuityscheduling/dashboard.html', context)

    except Exception as e:
        return render(request, 'acuityscheduling/dashboard.html', {'error': f"Analytics Engine Error: {str(e)}"})


@login_required
def sync_to_crm(request):
    """
    Manually trigger synchronization of Calendly appointments to Zoho CRM.
    """
    email = request.user.email
    try:
        # 1. Get Credentials
        credentials = CalendlyCredentials.objects.filter(email=email).first()
        if not credentials:
            return JsonResponse({'error': 'No Calendly credentials found'}, status=400)

        # 2. Get Zoho Token
        try:
            zoho_token = ZohoToken.objects.get(user=request.user)
        except ZohoToken.DoesNotExist:
            return JsonResponse({'error': 'Zoho account not connected'}, status=400)

        # 3. Refresh Calendly Token
        headers = check_and_refresh_token(credentials)
        if not headers:
            return JsonResponse({'error': 'Calendly authentication failed'}, status=401)

        # 4. Fetch Appointments (Respecting range filters if provided)
        user_response = requests.get('https://api.calendly.com/users/me', headers=headers)
        user_data = user_response.json()
        organization_uri = user_data['resource']['current_organization']
        user_uri = user_data['resource']['uri']

        now = datetime.now(timezone.utc)
        
        # Pull parameters from request
        start_date_val = request.GET.get('start_date', '')
        end_date_val = request.GET.get('end_date', '')

        # Default range: Last 30 days to Next 30 days if nothing specified
        if start_date_val:
            try:
                min_time = datetime.strptime(start_date_val, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                min_time = now - timedelta(days=30)
        else:
            min_time = now - timedelta(days=30)

        if end_date_val:
            try:
                max_time = datetime.strptime(end_date_val, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            except ValueError:
                max_time = now + timedelta(days=30)
        else:
            max_time = now + timedelta(days=30)
        
        events_url = 'https://api.calendly.com/scheduled_events'
        params = {
            'organization': organization_uri,
            'user': user_uri,
            'min_start_time': min_time.isoformat(),
            'max_start_time': max_time.isoformat(),
            'status': 'active',
            'count': 100
        }

        events_response = requests.get(events_url, headers=headers, params=params)
        events_response.raise_for_status()
        scheduled_events = events_response.json().get('collection', [])

        sync_count = 0
        error_count = 0

        # 5. Push to Zoho CRM
        for event in scheduled_events:
            # Get invitee details (needed for Zoho participants/contact info)
            invitee_response = requests.get(f"{event['uri']}/invitees", headers=headers).json()
            invitees = invitee_response.get('collection', [])
            
            for invitee in invitees:
                # Construct data for Zoho (Mapping fields from Calendly to Zoho format)
                # Following the logic in acuityscheduling_api.py
                start_dt = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(event['end_time'].replace('Z', '+00:00'))
                
                # Format for Zoho CRM v2 Events
                who_id = check_and_add_email(
                    {
                        "email": invitee.get('email'), 
                        "firstName": invitee.get('name', '').split(' ')[0], 
                        "lastName": ' '.join(invitee.get('name', '').split(' ')[1:]) or 'Calendly Guest'
                    }, 
                    "Contacts", 
                    request.user.id, 
                    only_contact=True
                )

                # Extract structured details for high-fidelity sync
                event_location = event.get('location') or {}
                location_str = event_location.get('join_url') or event_location.get('location') or event_location.get('type', 'Remote')
                guest_emails = [g.get('email') for g in event.get('event_guests', [])]
                
                # Consolidate all participants (Invitee + Guests)
                all_participants = [{"participant": invitee.get('email'), "type": "email"}]
                for g_email in guest_emails:
                    all_participants.append({"participant": g_email, "type": "email"})
                
                # Format Questions & Answers into a readable block
                qa_text = ""
                for qa in invitee.get('questions_and_answers', []):
                    qa_text += f"{qa.get('question', 'Q')}: {qa.get('answer', 'N/A')}\n"

                # Get External Calendar ID (Google/Outlook)
                external_id = (event.get('calendar_event') or {}).get('external_id', 'N/A')

                # Get User Settings for field mapping orchestration
                user_settings = Settings.objects.filter(user=request.user).first()
                mappings = user_settings.field_mappings if user_settings else {}

                description_text = (
                    f"--- HIGH FIDELITY CALENDLY SYNC ---\n"
                    f"Title: {event['name']}\n"
                    f"Invitee: {invitee.get('name')} ({invitee.get('email')})\n"
                    f"Status: {event.get('status', 'active').upper()}\n"
                    f"Location Detail: {location_str}\n"
                    f"Meeting Venue: {event_location.get('type')}\n"
                    f"External Event ID: {external_id}\n"
                    f"-----------------------------------\n"
                    f"QUESTIONS & ANSWERS:\n{qa_text or 'No questions provided.'}\n"
                    f"-----------------------------------\n"
                    f"GUESTS: {', '.join(guest_emails) or 'None'}\n"
                    f"-----------------------------------\n"
                    f"AUTO-GEN LINK: {event_location.get('join_url', 'N/A')}\n"
                    f"CANCEL URL: {invitee.get('cancel_url')}\n"
                    f"RESCHEDULE URL: {invitee.get('reschedule_url')}\n"
                    f"-----------------------------------\n"
                    f"Hub Trace ID: {event['uri'].split('/')[-1]}\n"
                    f"Source: Calendly Hub Integration"
                )

                # Base Event Data
                event_data = {
                    "Event_Title": f"Calendly: {event['name']} ({invitee.get('name')})",
                    "Subject": f"Calendly: {event['name']} ({invitee.get('name')})",
                    "Start_DateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "End_DateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "Participants": all_participants,
                    "Location": location_str,
                    "Description": description_text,
                    "Who_Id": who_id,
                    "Event_Source": "Calendly Hub"
                }

                # Orchestrate Custom Mappings
                mapping_payload = {
                    "Calendly_Event_Uri": event['uri'],
                    "Calendly_Invitee_Uri": invitee.get('uri'),
                    "Calendly_Cancel_Url": invitee.get('cancel_url'),
                    "Calendly_Reschedule_Url": invitee.get('reschedule_url'),
                    "Calendly_Event_Status": event.get('status'),
                    "Calendly_Question_Answer": qa_text,
                    "External_Event_ID": external_id,
                    "Meeting_Venue": event_location.get('type', 'Virtual')
                }

                for internal_key, value in mapping_payload.items():
                    zoho_field_name = mappings.get(internal_key)
                    if zoho_field_name:
                        # Use User-Defined Mapping
                        event_data[zoho_field_name] = value
                    else:
                        # Fallback to standard integration field names
                        event_data[internal_key] = value

                success = add_meeting_to_zoho_crm(event_data, request.user.id)
                if success:
                    sync_count += 1
                else:
                    error_count += 1

        return JsonResponse({
            'success': True, 
            'message': f'Sync complete. Processed {sync_count} meetings. Errors: {error_count}'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
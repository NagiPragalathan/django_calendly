from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
import requests
import json
import base64
from datetime import datetime, timedelta, timezone
from base.models import CalendlyCredentials, ZohoToken

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
            new_tokens = response.json()
            
            credentials.access_token = new_tokens['access_token']
            credentials.refresh_token = new_tokens['refresh_token']
            credentials.save()
            
        return {
            "Authorization": f"Bearer {credentials.access_token}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        return None

@login_required
def global_search(request):
    """
    Search across Calendly events and event types for matches.
    """
    query = request.GET.get('q', '').lower().strip()
    print(f"🔍 Global Search Triggered | Query: '{query}'")
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    email = request.user.email
    try:
        credentials = CalendlyCredentials.objects.filter(email=email).first()
        if not credentials:
            print("❌ Search Aborted: No credentials found.")
            return JsonResponse({'results': []})

        headers = check_and_refresh_token(credentials)
        if not headers:
            print("❌ Search Aborted: Token refresh failed.")
            return JsonResponse({'results': []})

        # Fetch current organization
        user_response = requests.get('https://api.calendly.com/users/me', headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        organization_uri = user_data['resource']['current_organization']

        results = []

        # 1. Search Event Types (Scheduling Links)
        print("📡 Fetching Event Types...")
        et_response = requests.get('https://api.calendly.com/event_types', headers=headers, params={'organization': organization_uri, 'count': 100})
        for et in et_response.json().get('collection', []):
            name = et['name'].lower()
            desc = (et.get('description') or '').lower()
            duration = str(et.get('duration', ''))
            
            if query in name or query in desc or query == duration:
                # Store full data for popup
                res_data = {
                    'name': et['name'],
                    'duration': et['duration'],
                    'kind': et.get('kind', 'Standard'),
                    'description': et.get('description', ''),
                    'color': et.get('color', '#4f46e5'),
                    'scheduling_url': et.get('scheduling_url', '#'),
                    'active': et.get('active', True),
                    'pooling_type': et.get('pooling_type', 'N/A'),
                    'internal_note': et.get('internal_note', 'No internal notes.'),
                    'type': 'Event Link'
                }
                
                results.append({
                    'type': 'Event Link',
                    'title': et['name'],
                    'subtitle': f"Duration: {et['duration']}m | {et.get('kind', 'Standard')}",
                    'url': '/appointments-types/',
                    'icon': 'ri-links-line',
                    'color': et.get('color', '#4f46e5'),
                    'full_data_json': json.dumps(res_data)
                })

        # 2. Search Scheduled Events (Past & Future)
        print("📡 Fetching Scheduled Events...")
        now = datetime.now(timezone.utc)
        start_min = now - timedelta(days=90) # Look back 90 days
        events_response = requests.get('https://api.calendly.com/scheduled_events', headers=headers, params={
            'organization': organization_uri,
            'min_start_time': start_min.isoformat(),
            'count': 100
        })
        
        for event in events_response.json().get('collection', []):
            event_name = event['name'].lower()
            event_status = event.get('status', '').lower()
            
            # Prepare meeting data
            start_time = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(event['end_time'].replace('Z', '+00:00'))
            
            meeting_data = {
                'name': event['name'],
                'start_time': start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M'),
                'status': event.get('status', 'Active').capitalize(),
                'location': event.get('location', {}),
                'calendar_event': event.get('calendar_event', {}),
                'created_at': datetime.fromisoformat(event['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d'),
                'type': 'Meeting'
            }

            matched = False
            # Basic match on name/status
            if query in event_name or query in event_status:
                matched = True
            
            # Detailed invitee fetch for ANY potential match
            try:
                invitee_res = requests.get(f"{event['uri']}/invitees", headers=headers, params={'count': 10})
                invitees_raw = invitee_res.json().get('collection', [])
                
                invitee_list = []
                for i in invitees_raw:
                    i_name = i.get('name', '')
                    i_email = i.get('email', '')
                    
                    if not matched and (query in i_name.lower() or query in i_email.lower()):
                        matched = True
                        
                    invitee_list.append({
                        'name': i_name,
                        'email': i_email,
                        'status': i.get('status', 'active'),
                        'timezone': i.get('timezone', 'UTC'),
                        'questions': i.get('questions_and_answers', [])
                    })
                
                meeting_data['invitees'] = invitee_list
            except:
                pass

            if matched:
                results.append({
                    'type': 'Meeting',
                    'title': event['name'],
                    'subtitle': f"{start_time.strftime('%b %d, %Y')} ({event.get('status', 'Active')})",
                    'url': '/appointments/' if start_time > now else '/past-appointments/',
                    'icon': 'ri-calendar-event-line',
                    'full_data_json': json.dumps(meeting_data)
                })

        print(f"✅ Search Finished: {len(results)} matches found.")
        return JsonResponse({'results': results[:15]})

    except Exception as e:
        print(f"🚨 Search Error: {str(e)}")
        return JsonResponse({'results': [], 'error': str(e)})

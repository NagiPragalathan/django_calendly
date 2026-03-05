from .models import ZohoToken, CalendlyCredentials
import requests
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import resolve

class UserDataMiddleware:
    """
    Middleware to add user-related data (e.g., image URL and company name) to the request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize default user_data
        request.user_data = {
            'name': 'Guest',
            'timezone': 'UTC',
            'timeFormat': '24h',
            'firstDayOfWeek': 0,
            'schedulingPage': '#'
        }

        # Add user-specific data only if the user is authenticated
        if request.user.is_authenticated:
            # Check Zoho connection status for template use - Always set this first
            # Use .first() is not None instead of .exists() to avoid Djongo recursion bug
            request.zoho_connected = ZohoToken.objects.filter(user=request.user).first() is not None
            if not request.zoho_connected:
                # Fallback: check by email if the direct user relationship has issues
                request.zoho_connected = ZohoToken.objects.filter(user__email=request.user.email).first() is not None
            
            try:
                # Retrieve Acuity credentials for the logged-in user
                credentials = CalendlyCredentials.objects.filter(email=request.user.email).first()
                
                if credentials:
                    # Attach the image URL to the request
                    if credentials.image_id:
                        request.image_url = credentials.image_id
                    else:
                        request.image_url = "https://avatars.githubusercontent.com/u/150781803?s=200&v=4"

                    # Attach the company name to the request
                    request.company_name = credentials.company_name

                    # Add new Acuity profile data fetch
                    try:
                        response = requests.get(
                            "https://acuityscheduling.com/api/v1/me",
                            auth=(credentials.user_id, credentials.api_key)
                        )
                        if response.status_code == 200:
                            acuity_data = response.json()
                            request.user_data = {
                                'name': acuity_data.get('name', credentials.company_name),
                                'timezone': acuity_data.get('timezone', 'UTC'),
                                'timeFormat': acuity_data.get('timeFormat', '24h'),
                                'firstDayOfWeek': acuity_data.get('firstDayOfWeek', 0),
                                'schedulingPage': acuity_data.get('schedulingPage', '#'),
                                'plan': acuity_data.get('plan', 'Free'),
                                'email': acuity_data.get('email', credentials.email)
                            }
                            print(request.user_data)
                    except:
                        # If API call fails, keep default user_data
                        pass
                else:
                    request.image_url = "https://avatars.githubusercontent.com/u/150781803?s=200&v=4"
                    request.company_name = 'susanoox'
            except Exception:
                request.image_url = "https://avatars.githubusercontent.com/u/150781803?s=200&v=4"
                request.company_name = 'susanoox'
            # Define pages that are exempt from the mandatory sync modal (setup/config pages)
            setup_url_names = [
                'list_credentials',
                'create_credentials',
                'edit_credentials',
                'delete_credentials',
                'settings_form',
                'appointment_types',
                'zoho_auth',
                'zoho_callback',
                'logout'
            ]
            from django.urls import resolve, Resolver404
            try:
                current_url_name = resolve(request.path_info).url_name
            except Resolver404:
                current_url_name = None
                
            request.is_setup_page = current_url_name in setup_url_names

        else:
            request.zoho_connected = False
            request.is_setup_page = False
            request.image_url = "https://avatars.githubusercontent.com/u/150781803?s=200&v=4"
            request.company_name = 'susanoox'
            public_url_names = [
                'login',
                'signup',
                'calendly_callback',
                'calendly_auth',
                'calendly_webhook_create_meeting',
                'list_credentials',
                'create_credentials',
                'edit_credentials',
                'delete_credentials'
            ]
            
            from django.urls import resolve, Resolver404
            try:
                current_url_name = resolve(request.path_info).url_name
            except Resolver404:
                current_url_name = None
                
            print(f"Current URL name: {current_url_name}", request.path_info)

            # Let static files and undefined routes pass through to standard 404/static handling
            # Only redirect if it's a known URL that requires auth
            if not request.user.is_authenticated and current_url_name and current_url_name not in public_url_names:
                return redirect('login')

        response = self.get_response(request)
        return response


class CalendlyUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def refresh_access_token(self, credentials):
        """Refresh the access token using the refresh token."""
        try:
            response = requests.post(
                'https://auth.calendly.com/oauth/token',
                data={
                    'client_id': 'your_client_id',  # Get from settings
                    'client_secret': 'your_client_secret',  # Get from settings
                    'grant_type': 'refresh_token',
                    'refresh_token': credentials.refresh_token
                }
            )

            if response.status_code == 200:
                token_data = response.json()
                # Update credentials in database
                credentials.access_token = token_data['access_token']
                if token_data.get('refresh_token'):  # Some OAuth providers send new refresh tokens
                    credentials.refresh_token = token_data['refresh_token']
                credentials.save()
                return credentials.access_token
            return None
        except requests.RequestException:
            return None

    def is_token_valid(self, access_token):
        """Check if the access token is still valid."""
        try:
            response = requests.get(
                'https://api.calendly.com/users/me',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_user_data(self, access_token):
        """Fetch user data from Calendly API."""
        try:
            response = requests.get(
                'https://api.calendly.com/users/me',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
            )
            if response.status_code == 200:
                return response.json().get('resource', {})
            return None
        except requests.RequestException:
            return None

    def __call__(self, request):
        if request.user.is_authenticated:
            # Try to get cached user data
            cache_key = f'calendly_user_{request.user.email}'
            user_data = cache.get(cache_key)

            if not user_data:
                # Get the most recent credentials for the user
                credentials = CalendlyCredentials.objects.filter(
                    email=request.user.email,
                    refresh_token__isnull=False
                ).first()

                if credentials:
                    access_token = credentials.access_token
                    
                    # Check if token is valid
                    if not self.is_token_valid(access_token):
                        # Try to refresh the token
                        access_token = self.refresh_access_token(credentials)
                    
                    if access_token:
                        # Fetch user data with valid token
                        user_data = self.get_user_data(access_token)
                        if user_data:
                            # Cache for 1 hour
                            cache.set(cache_key, user_data, 3600)
                            
                            # Also cache the token status
                            token_cache_key = f'calendly_token_valid_{request.user.email}'
                            cache.set(token_cache_key, True, 3300)  # Cache for 55 minutes
                    else:
                        # If we couldn't refresh the token, clear the cache
                        cache.delete(cache_key)
                        cache.delete(f'calendly_token_valid_{request.user.email}')

            # Add user data to request
            request.calendly_user = user_data

        return self.get_response(request) 

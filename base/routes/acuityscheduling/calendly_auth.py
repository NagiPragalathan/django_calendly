import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from base.models import CalendlyCredentials
from uuid import UUID  # Import UUID for conversion

def calendly_auth(request, credential_id):
    """Step 1: Redirect user to Calendly's OAuth authorization page."""
    # Ensure the credential_id is a string in the session
    if isinstance(credential_id, UUID):
        credential_id = str(credential_id)  # Convert UUID to string
    
    # Store the credential_id (as a string) in the session
    request.session['credential_id'] = credential_id

    auth_url = f"https://auth.calendly.com/oauth/authorize"
    redirect_url = f"{auth_url}?client_id={settings.CALENDLY_CLIENT_ID}&response_type=code&redirect_uri={settings.CALENDLY_REDIRECT_URI}"
    return redirect(redirect_url)

def calendly_callback(request):
    """Step 2: Handle the callback and exchange the authorization code for an access token."""
    code = request.GET.get('code')
    
    # Retrieve the credential_id from the session
    credential_id = request.session.get('credential_id')

    # Ensure credential_id is in the correct format (convert string back to UUID if needed)
    try:
        if credential_id:
            credential_id = UUID(credential_id)  # Convert the string back to UUID
    except ValueError:
        return JsonResponse({'error': 'Invalid credential ID format.'})

    print("Code:", code)
    print("Credential ID from session:", credential_id)

    if not code:
        return JsonResponse({'error': 'Authorization code not received.'})

    token_url = 'https://auth.calendly.com/oauth/token'
    data = {
        'grant_type': 'authorization_code',
        'client_id': settings.CALENDLY_CLIENT_ID,
        'client_secret': settings.CALENDLY_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.CALENDLY_REDIRECT_URI,
    }

    response = requests.post(token_url, data=data)

    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        request.session['calendly_access_token'] = access_token
        request.session['calendly_refresh_token'] = refresh_token

        # Retrieve the credentials by unique_id
        try:
            credential = CalendlyCredentials.objects.filter(unique_id=credential_id).update(access_token=access_token, refresh_token=refresh_token)
            return JsonResponse({'access_token': access_token, 'refresh_token': refresh_token})
        except CalendlyCredentials.DoesNotExist:
            return JsonResponse({'error': 'Credential ID not found in the database.'})

    else:
        return JsonResponse({'error': 'Failed to get access token', 'details': response.json()})

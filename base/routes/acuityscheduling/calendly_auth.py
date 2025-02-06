import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from base.models import CalendlyCredentials

def calendly_auth(request, credential_id):
    """Step 1: Redirect user to Calendly's OAuth authorization page."""
    # Build the redirect URL
    auth_url = f"https://auth.calendly.com/oauth/authorize"
    redirect_url = f"{auth_url}?ids={credential_id}&client_id={settings.CALENDLY_CLIENT_ID}&response_type=code&redirect_uri={settings.CALENDLY_REDIRECT_URI}"
    print(redirect_url, "redirect_url")  # For debugging purposes, you can remove this later
    return redirect(redirect_url)

def calendly_callback(request):
    """Step 2: Handle the callback and exchange the authorization code for an access token."""
    # Retrieve the authorization code and credential ID from the callback URL
    code = request.GET.get('code')
    credential_id = request.GET.get('ids')  # This is where we get the credential ID
    
    print(code, "code")  # For debugging
    print(credential_id, "credential_id")  # For debugging

    # If no code is present, return an error
    if not code:
        return JsonResponse({'error': 'Authorization code not received.'})

    # Set the URL for the token request to Calendly
    token_url = 'https://auth.calendly.com/oauth/token'
    data = {
        'grant_type': 'authorization_code',
        'client_id': settings.CALENDLY_CLIENT_ID,
        'client_secret': settings.CALENDLY_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.CALENDLY_REDIRECT_URI,
    }

    # Send the request to get the token
    response = requests.post(token_url, data=data)

    if response.status_code == 200:
        # Successfully obtained the tokens
        tokens = response.json()
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')

        # Store the tokens in the session (optional, for later use)
        request.session['calendly_access_token'] = access_token
        request.session['calendly_refresh_token'] = refresh_token

        # Now, we update the user's credentials with the new access and refresh tokens
        try:
            credential = CalendlyCredentials.objects.get(unique_id=credential_id)
            credential.access_token = access_token
            credential.refresh_token = refresh_token
            credential.save()

            # Return a success response
            return JsonResponse({'access_token': access_token, 'refresh_token': refresh_token})
        except CalendlyCredentials.DoesNotExist:
            return JsonResponse({'error': 'Credential ID not found in the database.'})

    else:
        # If the token request fails, return an error message
        return JsonResponse({'error': 'Failed to get access token', 'details': response.json()})

from django.shortcuts import render, redirect
from django.http import HttpResponse
import requests
from base.models import CalendlyCredentials

# Replace these values with your app's credentials
client_id = "GCkbxVoxJk2QtWYi"
client_secret = "LNHh7R6Ap5kfoYCvC5W4HumUfOXO8ARtiE0JvLdX"
redirect_uri = "http://127.0.0.1:8000/acuity/callback/"

def connect_acuity_scheduling(request):
    acuity_url = f"https://acuityscheduling.com/oauth2/authorize?response_type=code&scope=api-v1&client_id={client_id}&redirect_uri={redirect_uri}"
    access = CalendlyCredentials.objects.filter(user_id=request.user.id).exists()
    
    return render(request, 'acuityscheduling/as_connect.html', {'zoho_url': acuity_url, 'access': True})

def ac_callback(request):
    auth_code = request.GET.get('code')
    if not auth_code:
        return HttpResponse("Authorization code not provided", status=400)

    token_url = "https://acuityscheduling.com/oauth2/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code": auth_code,
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        CalendlyCredentials.objects.filter(user=request.user, access_token=access_token, refresh_token=refresh_token).delete()
        CalendlyCredentials.objects.create(user=request.user, access_token=access_token, refresh_token=refresh_token)
        return HttpResponse(f"Access Token: {access_token}<br>Refresh Token: {refresh_token}")
    else:
        return HttpResponse(f"Error: {response.json()}", status=response.status_code)

from django.shortcuts import render
import requests, uuid
from datetime import datetime
from base.models import ZohoToken


from Finalty.settings import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPE


def get_org_data(access_token):
    url = "https://www.zohoapis.com/crm/v2/org"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        org_data = response.json()
        return org_data['org'][0]['domain_name']
    else:
        return None


def zoho_index(request):
    zoho_url = f"https://accounts.zoho.com/oauth/v2/auth?scope={SCOPE}&client_id={CLIENT_ID}&response_type=code&access_type=offline&prompt=consent&redirect_uri={REDIRECT_URI}"
    print(request.user)
    return render(request, 'zoho/auth_page.html', {'zoho_url': zoho_url})



def zoho_callback(request):
    auth_code = request.GET.get('code')
    if not auth_code:
        return render(request, 'error.html', {"message": "Authorization code not found."})

    token_url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'code': auth_code
    }
    response = requests.post(token_url, data=payload)

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')

        # Fetch account name and org data from Zoho CRM
        org_data = get_org_data(access_token)
        
        print("org_data :", org_data)
        
        if org_data:
            try:
                ZohoToken.objects.get(org_data=org_data, user=request.user)
                ZohoToken.objects.filter(org_data=org_data, user=request.user).update(
                    refresh_token=refresh_token,
                    access_token=access_token,
                    created_at=datetime.now(),
                    unique_id=uuid.uuid4(),
                )
            except Exception as e:
                ZohoToken.objects.create(
                    user=request.user,
                    refresh_token=refresh_token,
                    access_token=access_token,
                    created_at=datetime.now(),
                    unique_id=uuid.uuid4(),
                    org_data=org_data
                )
            
            print("ZohoToken created successfully")
            return render(request, 'zoho/success.html', {
                "message": "Authentication complete! The Zoho account has been connected."
            })
        else:
            return render(request, 'zoho/error.html', {
                "message": "Organization data could not be fetched. Please try again."
            })
    else:
        return render(request, 'zoho/error.html', {
            "message": "Failed to generate tokens. Please try again later."
        })

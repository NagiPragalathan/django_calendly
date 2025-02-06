import requests

# Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.57c85253d1aa2d45b3f497082a83127a.611fc6edf04a30c1cee5e1b6c3d85620"

# Get Access Token
def get_access_token():
    url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, params=params)
    return response.json()["access_token"]

# Fetch All Fields in Events Module
def get_event_fields(access_token):
    url = "https://www.zohoapis.com/crm/v3/settings/fields?module=Events"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        fields = response.json().get("fields", [])
        print("\n✅ Custom Fields in Zoho CRM (Events Module):\n")
        for field in fields:
            print(f"Field Name: {field['field_label']}  |  API Name: {field['api_name']}")
    else:
        print("❌ Failed to fetch fields:", response.text)

# Run the script
if __name__ == "__main__":
    access_token = get_access_token()
    get_event_fields(access_token)

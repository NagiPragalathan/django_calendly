import requests

# Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.ee5f17b82fb54f15a0a7b19a1262546e.53be2445d4c2768bad2736bb239dfa63"

# Step 1: Get Access Token
def get_access_token():
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, params=params)
    response_json = response.json()
    if "access_token" in response_json:
        return response_json["access_token"]
    else:
        raise Exception(f"Failed to retrieve access token: {response_json}")

# Step 2: Add Custom Field to Events Module
def add_custom_field_to_events(access_token):
    # Use the Events module
    url = "https://www.zohoapis.com/crm/v3/settings/fields?module=Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": [
            {
                "field_label": "Test Sample",  # Name of the field displayed in the UI
                "api_name": "Test_Sample",    # Internal API name for the field
                "data_type": "text"          # Specify the data type of the field
            }
        ]
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Execute the script
try:
    # Step 1: Get the Access Token
    access_token = get_access_token()
    print("Access Token retrieved successfully!")

    # Step 2: Add the Custom Field to Events Module
    response = add_custom_field_to_events(access_token)
    print("Response from Zoho CRM API:")
    print(response)

except Exception as e:
    print(f"An error occurred: {e}")

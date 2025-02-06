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

# Step 2: Fetch All Fields from Events Module
def get_event_fields(access_token):
    url = "https://www.zohoapis.com/crm/v3/settings/fields?module=Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Step 3: Check if a field exists in the Events module
def check_field_exists(access_token, field_name):
    fields_response = get_event_fields(access_token)
    for field in fields_response.get("fields", []):
        if field["field_label"] == field_name:
            return True  # Field already exists
    return False  # Field does not exist

# Step 4: Create a new field in the Events module
def create_event_field(access_token, field_name, field_type="text", length=255):
    url = "https://www.zohoapis.com/crm/v3/settings/fields?module=Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "fields": [
            {
                "field_label": field_name,
                "api_name": field_name.replace(" ", "_"),    # Internal API name for the field
                "data_type": "text"          # Specify the data type of the field
            }
        ]
    }
    print(payload)
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Step 5: Check and Create Field if Needed
def ensure_field_exists(field_name):
    try:
        # Get access token
        access_token = get_access_token()
        print("Access Token retrieved successfully!")

        # Check if the field already exists
        if check_field_exists(access_token, field_name):
            print(f"Field '{field_name}' already exists in Zoho CRM Events module.")
        else:
            print(f"Field '{field_name}' does not exist. Creating now...")
            create_response = create_event_field(access_token, field_name)
            print(f"Field '{field_name}' created successfully:", create_response)
    
    except Exception as e:
        print(f"An error occurred: {e}")

ensure_field_exists("CustomEventField2")


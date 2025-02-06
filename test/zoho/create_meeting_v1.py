import requests
import json

# Credentials
# Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.ee5f17b82fb54f15a0a7b19a1262546e.53be2445d4c2768bad2736bb239dfa63"


# Get access token
def get_access_token(client_id, client_secret, refresh_token):
    url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.text}")

# Create custom fields
def create_custom_fields(access_token, module_name, fields):
    url = f"https://www.zohoapis.com/crm/v7/settings/fields?module={module_name}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"fields": fields}
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 201:
        print("Custom fields created successfully:", response.json())
    else:
        print(f"Failed to create custom fields: {response.text}")

# Main function
def main():
    try:
        # Step 1: Get the access token
        access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)

        # Step 2: Define the module name (e.g., Leads, Contacts, Events)
        module_name = "Leads"  # Replace with the actual module's API name

        # Step 3: Define the fields to be created
        fields = [
    {
        "field_label": "test name",
        "data_type": "text",
        "length": 150,
        "filterable": True,
        "tooltip": {
            "name": "static_text",
            "value": "test name"  # Shortened tooltip value
        },
        "profiles": [
        ],
        "external": {"type": "user", "show": True},
        "crypt": {"mode": "decryption"},
    }
]


        # Step 4: Create custom fields
        create_custom_fields(access_token, module_name, fields)

    except Exception as e:
        print(f"Error: {e}")

# Run the main function
if __name__ == "__main__":
    main()

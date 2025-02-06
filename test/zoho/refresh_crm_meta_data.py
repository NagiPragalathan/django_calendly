import requests
import json

# 🔹 Zoho OAuth Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.57c85253d1aa2d45b3f497082a83127a.611fc6edf04a30c1cee5e1b6c3d85620"

# 🔹 Step 1: Get Access Token
def get_access_token():
    url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"❌ Failed to get access token: {response.text}")

# 🔹 Step 2: Fetch All Fields in Events Module
def get_event_fields(access_token):
    url = "https://www.zohoapis.com/crm/v3/settings/fields?module=Events"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        fields = response.json().get("fields", [])
        print("\n✅ Current Custom Fields in Zoho CRM (Events Module):\n")
        field_names = {field["field_label"]: field["api_name"] for field in fields}
        for label, api in field_names.items():
            print(f"Field Name: {label}  |  API Name: {api}")
        return field_names
    else:
        print("❌ Failed to fetch fields:", response.text)
        return {}

# 🔹 Step 3: Create a New Custom Field (Fixed with `module` Parameter)
def create_event_field(access_token, field_label, field_api_name, field_type="text", length=255):
    url = "https://www.zohoapis.com/crm/v3/settings/fields"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "fields": [
            {
                "field_label": field_label,
                "api_name": field_api_name,
                "data_type": field_type,
                "length": length
            }
        ],
        "module": {  # ✅ Fixed: Added required "module" parameter
            "api_name": "Events"
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"✅ Field '{field_label}' created successfully!")
    else:
        print(f"❌ Failed to create field '{field_label}':", response.text)

# 🔹 Step 4: Main Function
def main():
    try:
        # 🔹 Get access token
        access_token = get_access_token()

        # 🔹 Check if 'CustomEventField' already exists
        existing_fields = get_event_fields(access_token)
        
        field_label = "CustomEventField"
        field_api_name = "CustomEventField"

        if field_label in existing_fields:
            print(f"⚠️ Field '{field_label}' already exists. Trying a new name...")
            field_label = "CustomEventField_1"
            field_api_name = "CustomEventField_1"

        # 🔹 Create the custom field (Fixed with `module` parameter)
        create_event_field(access_token, field_label, field_api_name)

    except Exception as e:
        print("❌ Error:", e)

# 🔹 Run the script
if __name__ == "__main__":
    main()

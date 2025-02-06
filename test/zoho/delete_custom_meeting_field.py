import requests
import json

# Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.06eb2802c5eb1ed66b1866f5c241541e.c883060e57bff28cd7e163b7fbe15daa"

# Step 1: Get Access Token
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
        raise Exception(f"Failed to get access token: {response.text}")

# Step 2: Fetch All Custom Fields from Events Module
def get_custom_fields(access_token):
    url = "https://www.zohoapis.com/crm/v3/settings/fields?module=Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        fields = response.json().get("fields", [])
        custom_fields = [
            {"id": field["id"], "api_name": field["api_name"], "field_label": field["field_label"]}
            for field in fields if field.get("custom_field", False)
        ]
        return custom_fields
    else:
        raise Exception("❌ Failed to fetch fields:", response.text)

# Step 3: Delete All Custom Fields (with module parameter)
def delete_custom_fields(access_token, custom_fields):
    for field in custom_fields:
        field_id = field["id"]
        field_label = field["field_label"]
        
        # ✅ Fix: Added module=Events as a query parameter
        delete_url = f"https://www.zohoapis.com/crm/v3/settings/fields/{field_id}?module=Events"

        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}"
        }

        response = requests.delete(delete_url, headers=headers)

        if response.status_code in [200, 202]:
            print(f"✅ Successfully deleted field: {field_label} ({field_id})")
        else:
            print(f"❌ Failed to delete field: {field_label} ({field_id}) - {response.text}")

# Step 4: Main Function
def main():
    try:
        access_token = get_access_token()
        custom_fields = get_custom_fields(access_token)

        if not custom_fields:
            print("✅ No custom fields found to delete.")
        else:
            print(f"🔹 Found {len(custom_fields)} custom fields to delete...")
            delete_custom_fields(access_token, custom_fields)

    except Exception as e:
        print("❌ Error:", e)

# Run the script
if __name__ == "__main__":
    main()

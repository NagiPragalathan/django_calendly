import requests
import json

# Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.57c85253d1aa2d45b3f497082a83127a.611fc6edf04a30c1cee5e1b6c3d85620"

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

# Step 2: Fetch API Names for Custom Fields
def get_event_fields(access_token):
    url = "https://www.zohoapis.com/crm/v3/settings/fields?module=Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        fields = response.json().get("fields", [])
        field_mapping = {field['field_label']: field['api_name'] for field in fields}
        return field_mapping
    else:
        raise Exception("Failed to fetch fields:", response.text)

# Step 3: Create an Event with Proper Currency Formatting
def create_event(access_token, field_mapping):
    url = "https://www.zohoapis.com/crm/v2/Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }

    event_data = {
        field_mapping.get("Title", "Event_Title"): "Real Estate Consultation",
        field_mapping.get("Subject", "Subject"): "Real Estate Consultation",
        field_mapping.get("From", "Start_DateTime"): "2025-01-30T15:00:00+05:30",
        field_mapping.get("To", "End_DateTime"): "2025-01-30T15:30:00+05:30",
        field_mapping.get("Participants", "Participants"): [{"participant": "nagipragalatham@gmail.com", "type": "email"}],
        field_mapping.get("Location", "Venue"): "Zoom",
        field_mapping.get("Description", "Description"): "Discussion on property investment options.",
        field_mapping.get("Contact Name", "Who_Id"): "2681636000019772001",
        field_mapping.get("Related To", "What_Id"): "2681636000013539001",
        "$se_module": "Accounts",  # ✅ REQUIRED: Specifies module for What_Id (e.g., Accounts, Deals)
        "SE_Who_Module": "Contacts",  # ✅ REQUIRED: Specifies module for Who_Id (e.g., Contacts, Leads)

        # 🟢 Custom Fields (Corrected Currency Format)
        field_mapping.get("Agent URL", "acuityscheduling1__AcuityURL"): "https://realestateconsultant.com/nagi",
        field_mapping.get("Calendar Name", "acuityscheduling1__Calendar_Name"): "Nagi's Calendar",
        field_mapping.get("Event Price", "acuityscheduling1__Event_Price"): 2000.00,  # ✅ Must be a number, not ₹2,000.00
        field_mapping.get("Calendar Email", "acuityscheduling1__Calendar_Email"): "agent@example.com"
    }

    payload = {"data": [event_data]}

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code in [200, 201]:
        print("✅ Event created successfully:", response.json())
    else:
        print("❌ Failed to create event:", response.text)

# Step 4: Main Function
def main():
    try:
        access_token = get_access_token()
        field_mapping = get_event_fields(access_token)  # Fetch field API names dynamically
        create_event(access_token, field_mapping)  # Use correct API names dynamically

    except Exception as e:
        print("❌ Error:", e)

# Run the script
if __name__ == "__main__":
    main()

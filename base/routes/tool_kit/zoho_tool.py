import requests
import json
from base.models import Settings, ZohoToken
from Finalty.settings import CLIENT_ID, CLIENT_SECRET

BASE_URL = "https://www.zohoapis.com/crm/v2"

##########################################################################################################
# Check the access token validity (Auth management)
##########################################################################################################
def check_access_token_validity(access_token):
    url = "https://www.zohoapis.com/crm/v7/settings/modules"  # Zoho CRM v7 API
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print("Access token is valid ✅")
        return True
    elif response.status_code == 401:
        print("Access token is invalid or expired ❌")
        return False
    else:
        print(f"Unexpected response: {response.status_code}, {response.json()}")
        return False

# Get the access token
def get_access_token(client_id, client_secret, refresh_token):
    url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.text}")

##########################################################################################################
# Create a new event in Zoho CRM (Meeting Management)
##########################################################################################################

def create_event(access_token, event_data):
    url = "https://www.zohoapis.com/crm/v2/Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "data": [event_data]
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 201:
        print("Event created successfully:", response.json())
        return True
    else:
        print("Failed to create event:", response.text)
        return False

def add_meeting_to_zoho_crm(event_data, user_id):
    zoho_token = ZohoToken.objects.get(user=user_id)
    access_token = zoho_token.access_token
    check = check_access_token_validity(access_token)
    if not check:
        access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
        ZohoToken.objects.filter(user=user_id).update(access_token=access_token)
    else:
        access_token = zoho_token.access_token
    try:
        create_event(access_token, event_data)
        return True
    except Exception as e:
        print("Error:", e)
        return False
    
    
def find_meeting_in_zoho(acuity_id, access_token):
    """
    Searches for an existing meeting in Zoho CRM using the Acuity_ID.
    """
    try:
        url = f"https://www.zohoapis.com/crm/v2/Events/search?criteria=(Acuity_ID:equals:{acuity_id})"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0]  # Return the first matching event
            else:
                return None
        else:
            print("Failed to search event in Zoho:", response.text)
            return None

    except Exception as e:
        print("Error searching for event in Zoho CRM:", e)
        return None

def update_meeting_in_zoho(access_token, updated_event_data):
    """
    Updates a meeting in Zoho CRM.
    """
    url = "https://www.zohoapis.com/crm/v2/Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "data": [updated_event_data]
    }
    
    response = requests.put(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        print("Event updated successfully:", response.json())
        return True
    else:
        print("Failed to update event:", response.text)
        return False


def update_meeting_in_zoho_crm(event_data, user_id):
    """
    Updates an existing meeting in Zoho CRM when an Acuity appointment is rescheduled.
    """
    try:
        # Get Zoho token
        zoho_token = ZohoToken.objects.get(user=user_id)
        access_token = zoho_token.access_token

        # Check if the access token is valid
        check = check_access_token_validity(access_token)
        if not check:
            access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
            ZohoToken.objects.filter(user=user_id).update(access_token=access_token)
        else:
            access_token = zoho_token.access_token

        # Find the existing meeting using Acuity ID
        zoho_event = find_meeting_in_zoho(event_data["Acuity_ID"], access_token)
        
        print("zoho_event", zoho_event)

        if not zoho_event:
            print(f"No existing meeting found in Zoho CRM with Acuity ID {event_data['Acuity_ID']}. Creating a new one instead.")
            return create_event(access_token, event_data)  # If not found, create a new event

        # Prepare updated event data
        updated_event_data = {
            "id": zoho_event["id"],  # Zoho CRM event ID
            "Start_DateTime": event_data["Start_DateTime"],
            "End_DateTime": event_data["End_DateTime"],
            "Location": event_data["Location"],
            "Description": event_data["Description"],
            "Participants": event_data["Participants"],
        }

        print("updated_event_data", updated_event_data)

        # Make API call to update the event in Zoho CRM
        response = update_meeting_in_zoho(access_token, updated_event_data)

        if response:
            print(f"Successfully updated meeting in Zoho CRM for Acuity ID {event_data['Acuity_ID']}.")
            return True
        else:
            print(f"Failed to update meeting in Zoho CRM for Acuity ID {event_data['Acuity_ID']}.")
            return False

    except Exception as e:
        print("Error updating meeting in Zoho CRM:", e)
        return False

def delete_meeting_from_zoho_crm(acuity_id, user_id):
    """
    Deletes a meeting from Zoho CRM based on Acuity_ID.
    """
    try:
        # Get Zoho token
        zoho_token = ZohoToken.objects.get(user=user_id)
        access_token = zoho_token.access_token

        # Check if access token is valid
        check = check_access_token_validity(access_token)
        if not check:
            access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
            ZohoToken.objects.filter(user=user_id).update(access_token=access_token)
        else:
            access_token = zoho_token.access_token

        # Find the existing meeting using Acuity ID
        zoho_event = find_meeting_in_zoho(acuity_id, access_token)

        if not zoho_event:
            print(f"No existing meeting found in Zoho CRM with Acuity ID {acuity_id}.")
            return False

        # Get Zoho Event ID
        event_id = zoho_event["id"]

        # Call API to delete the event
        url = f"https://www.zohoapis.com/crm/v2/Events/{event_id}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.delete(url, headers=headers)

        if response.status_code == 200:
            print(f"Successfully deleted meeting with Acuity ID {acuity_id} in Zoho CRM.")
            return True
        else:
            print(f"Failed to delete meeting in Zoho CRM: {response.text}")
            return False

    except Exception as e:
        print("Error deleting meeting in Zoho CRM:", e)
        return False


##########################################################################################################
# Create a new contact into Zoho CRM
##########################################################################################################

def search_email(access_token, email, module):
    """Search for an email in the specified module (Leads or Contacts)."""
    url = f"{BASE_URL}/{module}/search"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    params = {"email": email}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 204:
            return None  # No records found
        response.raise_for_status()
        data = response.json()
        
        if "data" in data:
            return data["data"][0]  # Return first matching record
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error searching {module}: {e}")
        return None

def create_new_record(access_token, module, user_data):
    """Create a new record in the specified module."""
    url = f"{BASE_URL}/{module}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    Module = "Acuity Scheduling"
    try:
        settings = Settings.objects.get(user_id=user_data.get("app_user_id")) 
        Module = settings.lead_source   
    except Exception as e:
        Module = "Acuity Scheduling"
    
    user_data = {
        "First_Name": user_data.get("firstName"),
        "Last_Name": user_data.get("lastName"),
        "Email": user_data.get("email"),
        "Phone": user_data.get("phone"),
        "Lead_Source": Module,
    }
    payload = {"data": [user_data]}  # Zoho API requires data inside a list


    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if "data" in data and data["data"][0].get("code") == "SUCCESS":
            return data["data"][0]["details"]["id"]  # Return the created user ID
        else:
            print(f"❌ Failed to create record. Response: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating record in {module}: {e}")
        return None

def check_and_add_email(user_data, module, only_contact=False):
    """Check if the email exists, if not, create a new record."""
    print(user_data, "user_data")
    zoho_token = ZohoToken.objects.get(user=user_data.get("app_user_id"))
    access_token = zoho_token.access_token
    check = check_access_token_validity(access_token)
    if not check:
        access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
        ZohoToken.objects.filter(user=user_data.get("app_user_id")).update(access_token=access_token)
    else:
        access_token = zoho_token.access_token


    if not access_token:
        print("❌ Unable to continue without a valid access token.")
        return

    email = user_data.get("email")
    
    # Check if the email already exists
    existing_user = search_email(access_token, email, module)
    
    if only_contact:
        existing_user = search_email(access_token, email, "Contacts")
        if existing_user:
            print(f"✅ Email '{email}' already exists in {"Contacts"}. User ID: {existing_user['id']}")
            return existing_user["id"]
        else:
            print(f"⚠️ Email '{email}' not found in {"Contacts"}. Creating new record...")

            # Create a new record
            new_user_id = create_new_record(access_token, "Contacts", user_data)
            if new_user_id:
                print(f"✅ New user created in {"Contacts"} with ID: {new_user_id}")
            return new_user_id
    
    if existing_user:
        print(f"✅ Email '{email}' already exists in {module}. User ID: {existing_user['id']}")
        return existing_user["id"]
    else:
        print(f"⚠️ Email '{email}' not found in {module}. Creating new record...")

        # Create a new record
        new_user_id = create_new_record(access_token, module, user_data)
        if new_user_id:
            print(f"✅ New user created in {module} with ID: {new_user_id}")
        return new_user_id

##########################################################################################################
# Create a new custom field in Zoho CRM
##########################################################################################################

def get_event_fields(access_token):
    url = "https://www.zohoapis.com/crm/v3/settings/fields?module=Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def check_field_exists(access_token, field_name):
    fields_response = get_event_fields(access_token)
    for field in fields_response.get("fields", []):
        if field["field_label"] == field_name:
            return True
    return False 

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
                "api_name": field_name.replace(" ", "_"),
                "data_type": "text"
            }
        ]
    }
    print(payload)
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Step 5: Check and Create Field if Needed
def ensure_field_exists(user_obj, field_name):
    zoho_token = ZohoToken.objects.get(user=user_obj)
    access_token = zoho_token.access_token
    check = check_access_token_validity(access_token)
    print(check, "check")
    if not check:
        access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
        ZohoToken.objects.filter(user=user_obj).update(access_token=access_token)
    else:
        access_token = zoho_token.access_token
    try:
        if check_field_exists(access_token, field_name):
            print(f"Field '{field_name}' already exists in Zoho CRM Events module.")
        else:
            print(f"Field '{field_name}' does not exist. Creating now...")
            create_response = create_event_field(access_token, field_name)
            print(f"Field '{field_name}' created successfully:", create_response)
    
    except Exception as e:
        print(f"An error occurred: {e}")
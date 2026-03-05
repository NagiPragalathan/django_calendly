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
    
    # Extract Notes_Data if present and remove it from the direct event payload
    note_content = event_data.pop("Notes_Data", None)
    
    payload = {
        "data": [event_data]
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 201:
        res_json = response.json()
        print("Event created successfully:", res_json)
        
        # Protocol: If dynamic notes provided, attach them as a separate Zoho Note
        if note_content and "data" in res_json:
            event_id = res_json["data"][0]["details"]["id"]
            add_note_to_zoho_record(access_token, "Events", event_id, note_content)
            
        return res_json # Return the full response for ID extraction
    else:
        print("Failed to create event:", response.text)
        return False

def add_note_to_zoho_record(access_token, module, record_id, note_content):
    """
    Creates an attached Note for a specific Zoho record.
    Useful for rich-text designs that don't fit in standard text fields.
    """
    url = f"https://www.zohoapis.com/crm/v2/Notes"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "data": [
            {
                "Note_Title": "Meeting Intelligence Dispatch",
                "Note_Content": note_content,
                "Parent_Id": record_id,
                "$se_module": module
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 201:
            print(f"✅ Rich detail attached as Note for {module} {record_id}")
            return True
        else:
            print(f"⚠️ Note Attachment Failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Note Engine Error: {e}")
        return False

def get_zoho_record(module, record_id, access_token):
    """Fetch record details from Zoho CRM by module and ID."""
    url = f"https://www.zohoapis.com/crm/v2/{module}/{record_id}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0]
    return None

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

def find_calendly_meeting_in_zoho(event_data, access_token):
    """
    Advanced multi-layered search for existing Calendly meetings in Zoho CRM.
    1. Primary: Search by unique Calendly Invitee URI (with quotes)
    2. Fallback: Search by Subject + Start DateTime (Human-readable uniqueness)
    """
    try:
        # Check Invitee URI (Most precise)
        invitee_uri = event_data.get("Calendly_Invitee_Uri")
        if invitee_uri:
            url = f"https://www.zohoapis.com/crm/v2/Events/search?criteria=(Calendly_Invitee_Uri:equals:\"{invitee_uri}\")"
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    print(f"✅ Deduplication Success: Match found via Invitee URI.")
                    return data["data"][0]

        # Check Event URI (Secondary)
        event_uri = event_data.get("Calendly_Event_Uri")
        if event_uri:
            url = f"https://www.zohoapis.com/crm/v2/Events/search?criteria=(Calendly_Event_Uri:equals:\"{event_uri}\")"
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    print(f"✅ Deduplication Success: Match found via Event URI.")
                    return data["data"][0]

        # Protocol 3: Subject + Time Fallback
        subject = event_data.get("Subject")
        start_time = event_data.get("Start_DateTime")
        if subject and start_time:
            url = f"https://www.zohoapis.com/crm/v2/Events/search?criteria=(Subject:equals:\"{subject}\")"
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for record in data.get("data", []):
                    if record.get("Start_DateTime")[:19] == start_time[:19]:
                        print(f"✅ Deduplication Fallback: Match found via Fingerprint.")
                        return record

        return None
    except Exception as e:
        print(f"⚠️ Search Logic Error: {e}")
        return None

def add_meeting_to_zoho_crm(event_data, user_id):
    print("Orchestrating High-Fidelity Sync...")
    zoho_token = ZohoToken.objects.get(user=user_id)
    access_token = zoho_token.access_token
    
    check = check_access_token_validity(access_token)
    if not check:
        access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
        ZohoToken.objects.filter(user=user_id).update(access_token=access_token)
    else:
        access_token = zoho_token.access_token

    try:
        # Step 1: Execute Deduplication Intelligence
        existing_event = find_calendly_meeting_in_zoho(event_data, access_token)
        
        if existing_event:
            print(f"♻️ Update Protocol: Refreshed detail for Zoho ID: {existing_event['id']}")
            event_data["id"] = existing_event["id"]
            return update_meeting_in_zoho(access_token, event_data)
        
        # Step 2: Proceed with Creation if no match found
        print("🆕 Creation Protocol: Launching new record in Zoho CRM...")
        return create_event(access_token, event_data)
    except Exception as e:
        print(f"❌ Critical Sync Failure: {e}")
        return False

def update_meeting_in_zoho(access_token, updated_event_data):
    """
    Updates a meeting in Zoho CRM.
    """
    url = "https://www.zohoapis.com/crm/v2/Events"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    
    # Extract Notes_Data if present
    note_content = updated_event_data.pop("Notes_Data", None)
    
    payload = {
        "data": [updated_event_data]
    }
    
    response = requests.put(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        print("Event updated successfully:", response.json())
        
        # If dynamic notes provided during update, attach them too
        if note_content and updated_event_data.get("id"):
            add_note_to_zoho_record(access_token, "Events", updated_event_data["id"], note_content)
            
        return True
    else:
        print("Failed to update event:", response.text)
        return False


def update_meeting_in_zoho_crm(event_data, user_id):
    """
    Updates an existing meeting in Zoho CRM.
    Supports both Acuity and Calendly lifecycles.
    """
    try:
        zoho_token = ZohoToken.objects.get(user=user_id)
        access_token = zoho_token.access_token

        check = check_access_token_validity(access_token)
        if not check:
            access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
            ZohoToken.objects.filter(user=user_id).update(access_token=access_token)
        else:
            access_token = zoho_token.access_token

        # Step 1: Locate existing record
        zoho_event = None
        
        # Calendly Route
        if event_data.get("Calendly_Event_URI"):
            zoho_event = find_calendly_meeting_in_zoho(event_data, access_token)
        
        # Acuity Route (Legacy)
        if not zoho_event and event_data.get("Acuity_ID"):
            zoho_event = find_meeting_in_zoho(event_data["Acuity_ID"], access_token)

        if not zoho_event:
            print(f"⚠️ Reschedule Scoped: No existing record found. Scaling to creation...")
            return create_event(access_token, event_data)

        # Step 2: Prepare updated payload
        event_data["id"] = zoho_event["id"]
        
        # Make API call to update the event in Zoho CRM
        response = update_meeting_in_zoho(access_token, event_data)

        if response:
            print(f"✅ Successfully synchronized update for Zoho ID {zoho_event['id']}")
            return True
        else:
            print(f"❌ Update Rejection for Zoho ID {zoho_event['id']}")
            return False

    except Exception as e:
        print(f"❌ Synchronizer Lifecycle Exception: {e}")
        return False

def delete_meeting_from_zoho_crm(technical_id, user_id):
    """
    Deletes a meeting from Zoho CRM.
    Supports both legacy Acuity IDs and modern Calendly URIs.
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

        # Find the existing meeting (Multi-Protocol Search)
        # 1. Try Calendly URI Search
        zoho_event = None
        if "calendly.com" in str(technical_id):
            url = f"https://www.zohoapis.com/crm/v2/Events/search?criteria=(Calendly_Event_Uri:equals:\"{technical_id}\")"
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
            res = requests.get(url, headers=headers)
            if res.status_code == 200 and "data" in res.json():
                zoho_event = res.json()["data"][0]
        
        # 2. Fallback to Acuity ID search if not found or not a URI
        if not zoho_event:
            zoho_event = find_meeting_in_zoho(technical_id, access_token)

        if not zoho_event:
            print(f"⚠️ Deletion Scoped: No existing record found for ID {technical_id}.")
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
            print(f"✅ Successfully decommissioned record {event_id} in Zoho CRM.")
            return True
        else:
            print(f"❌ Deletion Rejection: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Deletion Logic Error: {e}")
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
    
    user_data_payload = {
        "First_Name": user_data.get("firstName"),
        "Last_Name": user_data.get("lastName") or ".", # Zoho Mandatory: Fallback to period for anonymous invitees
        "Email": user_data.get("email"),
        "Phone": user_data.get("phone"),
        "Lead_Source": Module,
    }
    payload = {"data": [user_data_payload]}  # Zoho API requires data inside a list


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

def check_and_add_email(user_data, module, user_id, only_contact=False):
    """Check if the email exists, if not, create a new record."""
    print(user_data, "user_data")
    zoho_token = ZohoToken.objects.get(user=user_id)
    access_token = zoho_token.access_token
    check = check_access_token_validity(access_token)
    if not check:
        access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
        ZohoToken.objects.filter(user=user_id).update(access_token=access_token)
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

def get_module_fields(access_token, module):
    """Retrieve all fields for a specific Zoho CRM module."""
    url = f"https://www.zohoapis.com/crm/v2/settings/fields?module={module}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def get_event_fields(access_token):
    return get_module_fields(access_token, "Events")

def check_field_exists(access_token, field_name):
    fields_response = get_event_fields(access_token)
    for field in fields_response.get("fields", []):
        if field["field_label"] == field_name:
            return True
    return False 

def create_module_field(access_token, module, field_name, field_type="text"):
    """Create a new custom field in any specified Zoho CRM module."""
    url = f"https://www.zohoapis.com/crm/v3/settings/fields?module={module}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "fields": [
            {
                "field_label": field_name,
                "api_name": field_name.replace(" ", "_"),
                "data_type": field_type
            }
        ]
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def create_event_field(access_token, field_name):
    # Maintain backward compatibility but point to the generic version
    return create_module_field(access_token, "Events", field_name)

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
To include the "Contact Name" in the Events module when creating an event in Zoho CRM, you need to properly add the Who_Id field in your payload. The Who_Id field represents the contact or lead associated with the event.

Here’s the updated code snippet with the inclusion of the Contact Name (or Who_Id):

Updated Code
python
Copy
Edit
import requests
import json

# Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.57c85253d1aa2d45b3f497082a83127a.611fc6edf04a30c1cee5e1b6c3d85620"

old_access_token = "1000.57c85253d1aa2d45b3f497082a83127a.611fc6edf04a30c1cee5e1b6c3d85620"


def check_access_token_validity(access_token):
    url = "https://www.zohoapis.com/crm/v2/users/me"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return True
    elif response.status_code == 401:
        return False
    else:
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

# Create a new event in Zoho CRM
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
    else:
        print("Failed to create event:", response.text)

# Main function
def main():
    try:
        check = check_access_token_validity(old_access_token)
        if not check:
            # Get access token
            access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
        else:
            access_token = old_access_token
            
        # Define event data
        event_data = {
            "Event_Title": "Project Kickoff Meeting",
            "Subject": "Project Kickoff Meeting",
            "Start_DateTime": "2025-01-27T10:00:00+05:30",
            "End_DateTime": "2025-01-27T11:00:00+05:30",
            "Participants": [{"participant": "nagi@gmail.com", "type": "email"}],
            "Location": "Zoom",
            "Description": "Discussing project milestones and deliverables.",
            "Who_Id": "1234567890123456789"  # Replace with the actual Contact ID
        }
        
        # Create the event
        create_event(access_token, event_data)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
Key Details:
Who_Id Field:

This represents the Contact or Lead ID in Zoho CRM.
Replace "1234567890123456789" with the actual contact ID retrieved from Zoho CRM. You can get the Contact ID by querying the Contacts module using the Zoho CRM API.
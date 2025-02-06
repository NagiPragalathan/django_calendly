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
        # event_data = {
        #     "Event_Title": "Project Kickoff Meeting",
        #     "Subject": "Project Kickoff Meeting",
        #     "Start_DateTime": "2025-01-27T10:00:00+05:30",
        #     "End_DateTime": "2025-01-27T11:00:00+05:30",
        #     "Participants": [{"participant": "nagi@gmail.com", "type": "email"}],
        #     "Location": "Zoom",
        #     "Description": "Discussing project milestones and deliverables."
        # }
        # event_data = event_data = {
        #     "Event_Title": "testReal Estate Consultation to Nagi Pragalathan", 
        #     "Subject": "testReal Estate Consultation to Nagi Pragalathan", 
        #     "Start_DateTime": "2025-01-30T15:00:00+05:30", 
        #     "End_DateTime": "2025-01-30T15:30:00+05:30", 
        #     "Participants": [{"participant": "nagipragalatham@gmail.com", "type": "email"}], 
        #     "Location": "Zoom", 
        #     "Description": "Name: Nagi Pragalathan\nPhone: (740) 126-8095\nEmail: nagipragalatham@gmail.com\nPrice: ₹2,000.00\n", 
        #     "Who_Id": "2681636000019772001",  # Contact or Lead ID
        #     "What_Id": "2681636000013539001",  # Account ID
        #     "$se_module": "Accounts",  # Make sure this matches the module of What_Id  # Accounts or Deals
        #     "SE_Who_Module": "Contacts"  # Ensure this matches the Who_Id module # Contacts or Leads
        # }
        event_data = {'Event_Title': 'test Real Estate Cunsultaton to Nagi Pragalathan', 'Subject': 'test Real Estate Cunsultaton to Nagi Pragalathan', 'Start_DateTime': '2025-02-05T10:00:00+05:30', 'End_DateTime': '2025-02-05T10:30:00+05:30', 'Participants': [{'participant': 'nagipragalatham@gmail.com', 'type': 'email'}], 'Location': 'Zoom', 'Description': 'Name: Nagi Pragalathan\nPhone: (740) 126-8095\nEmail: nagipragalatham@gmail.com\nPrice: ₹2,000.00\n', 'Who_Id': '2681636000019772001', 'Acuity_Client_Link': '10', 'Acuity_ID': '20', 'Acuity_Agent_Link': '30', 'Acuity_Calendar_Name': '40', 'Acuity_Calendar_Email': '50', 'Acuity_Event_Price': '60'}

        # Create the event
        create_event(access_token, event_data)

    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()

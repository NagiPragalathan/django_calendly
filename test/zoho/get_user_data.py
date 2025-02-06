import requests
import json

# Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.57c85253d1aa2d45b3f497082a83127a.611fc6edf04a30c1cee5e1b6c3d85620"

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

# Get lead data by lead ID
def get_lead_data(access_token, lead_id):
    url = f"https://www.zohoapis.com/crm/v2/Leads/{lead_id}"  # Endpoint for Lead records
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("Lead data retrieved successfully:")
        print(json.dumps(response.json(), indent=4))
    elif response.status_code == 204:
        print("No content found for the provided Lead ID.")
    else:
        print(f"Failed to get lead data: {response.status_code}")
        print(response.json())

# Main function
def main():
    try:
        # Get access token
        access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
        
        # Specify the lead ID you want to fetch
        lead_id = "2681636000020151001"  # Replace with the actual Lead ID
        
        # Get lead data
        get_lead_data(access_token, lead_id)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()

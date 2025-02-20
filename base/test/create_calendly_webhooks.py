import requests
import json

# Your access token
ACCESS_TOKEN = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiSldUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzQwMDQ2NzQ4LCJqdGkiOiJkZTVkYTY2Ny0yOTI3LTRjOWQtYTY1Ni1jZGFkNGZlOGRjZWMiLCJ1c2VyX3V1aWQiOiI1MTUyMTM3OS1lMzE4LTRmZjItYTUyYi01OTg2NWEyYmZkYjEiLCJhcHBfdWlkIjoibW1nekgzTUdIT2w0WHhTb19TMlJkODhOSGtRWE50cDJCQjFvQmNIdWVfcyIsImV4cCI6MTc0MDA1Mzk0OH0.tzFqZ_wxU3raR-KejWoV96g1vJ-tZP-dml3E4Wv3kN3DvOTMlBEhP23RcihW_0b_4GyRTo_i51jS5s66xZZwaA"

# API Base URL
BASE_URL = "https://api.calendly.com"

# Define webhook URL (this will be your endpoint where the events will be sent)
WEBHOOK_URL = "https://webhook.site/1306eab1-748b-4c6a-a82d-fbe7aed74bf0"  # Replace with your actual webhook receiver URL

# Step 1: Retrieve user info to get organization and user URI
def get_user_info(access_token: str):
    url = f"{BASE_URL}/users/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        # Extract organization URL and user URI
        organization_url = user_data["resource"].get("current_organization")
        user_uri = user_data["resource"].get("uri")

        return organization_url, user_uri
    else:
        print(f"Error retrieving user info: {response.status_code}")
        return None, None

# Step 2: Create webhook subscription
def create_webhook_subscription(access_token: str, organization_url: str, user_uri: str, webhook_url: str):
    url = f"{BASE_URL}/webhook_subscriptions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Set the request body
    payload = {
        "url": webhook_url,
        "events": ["invitee.created", "invitee.canceled"],
        "organization": organization_url,
        "user": user_uri,
        "scope": "user"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 201:
        print("Webhook created successfully!")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Failed to create webhook: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    # Get organization and user URIs
    organization_url, user_uri = get_user_info(ACCESS_TOKEN)

    if organization_url and user_uri:
        # Create the webhook subscription
        create_webhook_subscription(ACCESS_TOKEN, organization_url, user_uri, WEBHOOK_URL)
    else:
        print("Could not retrieve user info or organization details.")

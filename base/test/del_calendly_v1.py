import requests
import json

# Replace with your actual access token
ACCESS_TOKEN = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiSldUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzQwMDMyOTcwLCJqdGkiOiJkN2Y0MDUwMi01MzI0LTRmYmYtOWUxMC0wMWI3ZTBkNGQzZjUiLCJ1c2VyX3V1aWQiOiI1MTUyMTM3OS1lMzE4LTRmZjItYTUyYi01OTg2NWEyYmZkYjEiLCJhcHBfdWlkIjoibW1nekgzTUdIT2w0WHhTb19TMlJkODhOSGtRWE50cDJCQjFvQmNIdWVfcyIsImV4cCI6MTc0MDA0MDE3MH0.waIwdjVAjx8iYzPXuhXwwv-PfFBD48-nucuiyjI0d6hlojI00ECHcStLBGvEOEo6h4HlCMfFbWMzIqFnNL1b7g"

# Replace with your actual organization URI
ORGANIZATION_URI = "https://api.calendly.com/organizations/3f0ebc83-99f6-4b0f-9d3a-ccf2df1f383f"

# Calendly API base URL
BASE_URL = "https://api.calendly.com/webhook_subscriptions"

def get_all_webhooks(access_token, organization_uri, scope="organization"):
    """
    Fetch all webhook subscriptions for a given organization or user.
    
    Args:
        access_token (str): Calendly API OAuth access token.
        organization_uri (str): The organization URI to filter webhooks.
        scope (str): Scope of the webhooks ('organization' or 'user').
    
    Returns:
        List of webhook UUIDs.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    params = {
        "organization": "https://api.calendly.com/organizations/3f0ebc83-99f6-4b0f-9d3a-ccf2df1f383f", 
        "count": "1", 
        "scope": "user",
        "user": "https://api.calendly.com/users/51521379-e318-4ff2-a52b-59865a2bfdb1"  # Add the user parameter
    }

    webhook_uuids = []
    url = BASE_URL

    while url:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(data)
            webhooks = data.get("collection", [])
            
            # Extract webhook UUIDs
            webhook_uuids.extend([webhook["uri"].split("/")[-1] for webhook in webhooks])
            
            # Check for pagination
            next_page_token = data.get("pagination", {}).get("next_page_token")
            if next_page_token:
                url = f"{BASE_URL}?count=100&page_token={next_page_token}"
            else:
                url = None
        else:
            print(f"Error fetching webhooks: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
            return None

    return webhook_uuids

def delete_webhook(access_token, webhook_uuid):
    """
    Deletes a webhook subscription by UUID.
    
    Args:
        access_token (str): Calendly API OAuth access token.
        webhook_uuid (str): The UUID of the webhook to delete.
    """
    url = f"{BASE_URL}/{webhook_uuid}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.delete(url, headers=headers)

    if response.status_code == 204:
        print(f"✅ Webhook {webhook_uuid} deleted successfully.")
    else:
        print(f"❌ Failed to delete webhook {webhook_uuid}: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    # Get all webhook UUIDs
    webhook_uuids = get_all_webhooks(ACCESS_TOKEN, ORGANIZATION_URI)

    if webhook_uuids:
        print(f"\nFound {len(webhook_uuids)} webhooks to delete...\n")
        for webhook_uuid in webhook_uuids:
            delete_webhook(ACCESS_TOKEN, webhook_uuid)
    else:
        print("No webhooks found.")

import requests
import json

# Replace with your actual Calendly API access token
ACCESS_TOKEN = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiSldUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzQwMDMyOTcwLCJqdGkiOiJkN2Y0MDUwMi01MzI0LTRmYmYtOWUxMC0wMWI3ZTBkNGQzZjUiLCJ1c2VyX3V1aWQiOiI1MTUyMTM3OS1lMzE4LTRmZjItYTUyYi01OTg2NWEyYmZkYjEiLCJhcHBfdWlkIjoibW1nekgzTUdIT2w0WHhTb19TMlJkODhOSGtRWE50cDJCQjFvQmNIdWVfcyIsImV4cCI6MTc0MDA0MDE3MH0.waIwdjVAjx8iYzPXuhXwwv-PfFBD48-nucuiyjI0d6hlojI00ECHcStLBGvEOEo6h4HlCMfFbWMzIqFnNL1b7g"


# Calendly API Base URL
BASE_URL = "https://api.calendly.com"

def get_user_info(access_token):
    """
    Retrieve the user's organization and user URI dynamically.

    Args:
        access_token (str): Calendly API OAuth access token.

    Returns:
        tuple: (organization_uri, user_uri)
    """
    url = f"{BASE_URL}/users/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user_data = response.json()
        organization_uri = user_data["resource"]["current_organization"]
        user_uri = user_data["resource"]["uri"]
        return organization_uri, user_uri
    else:
        print(f"❌ Failed to fetch user info: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return None, None

def get_all_webhooks(access_token, organization_uri, user_uri, scope="user"):
    """
    Fetch all webhook subscriptions for a given organization or user.

    Args:
        access_token (str): Calendly API OAuth access token.
        organization_uri (str): The organization URI.
        user_uri (str): The user URI.
        scope (str): Scope of the webhooks ('organization' or 'user').

    Returns:
        List of webhook UUIDs.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    params = {
        "organization": organization_uri,
        "user": user_uri,
        "count": 100,  # Max limit per request
        "scope": scope
    }
    
    print(params)

    webhook_uuids = []
    url = f"{BASE_URL}/webhook_subscriptions"

    while url:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            print(data)  # Debugging: Print API response
            webhooks = data.get("collection", [])

            # Extract webhook UUIDs
            webhook_uuids.extend([webhook["uri"].split("/")[-1] for webhook in webhooks])

            # Handle pagination
            next_page_token = data.get("pagination", {}).get("next_page_token")
            if next_page_token:
                url = f"{BASE_URL}/webhook_subscriptions?count=100&page_token={next_page_token}"
            else:
                url = None
        else:
            print(f"❌ Error fetching webhooks: {response.status_code}")
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
    url = f"{BASE_URL}/webhook_subscriptions/{webhook_uuid}"
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
    # Get dynamic organization and user URIs
    organization_uri, user_uri = get_user_info(ACCESS_TOKEN)

    if organization_uri and user_uri:
        # Get all webhook UUIDs
        webhook_uuids = get_all_webhooks(ACCESS_TOKEN, organization_uri, user_uri)

        if webhook_uuids:
            print(f"\nFound {len(webhook_uuids)} webhooks to delete...\n")
            for webhook_uuid in webhook_uuids:
                delete_webhook(ACCESS_TOKEN, webhook_uuid)
        else:
            print("No webhooks found.")
    else:
        print("❌ Could not retrieve organization and user URIs.")

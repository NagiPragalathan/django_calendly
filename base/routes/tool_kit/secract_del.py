import requests

# Replace with your API credentials
API_USER_ID = "15632977"
API_SECRET_KEY = "0000b6ceb812a72dde36b6c41a8b057f"

# Base URL for Acuity Scheduling API
BASE_URL = "https://acuityscheduling.com/api/v1/webhooks"

def get_webhooks(API_USER_ID, API_SECRET_KEY):
    try:
        # Get all webhooks
        response = requests.get(
            BASE_URL,
            auth=(API_USER_ID, API_SECRET_KEY)
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to retrieve webhooks. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred while retrieving webhooks: {e}")
        return None

def delete_webhook(webhook_id):
    try:
        # Delete a webhook by ID
        delete_url = f"{BASE_URL}/{webhook_id}"
        response = requests.delete(
            delete_url,
            auth=(API_USER_ID, API_SECRET_KEY)
        )
        if response.status_code == 204:  # HTTP 204 No Content means success
            print(f"Webhook ID {webhook_id} deleted successfully.")
        else:
            print(f"Failed to delete webhook ID {webhook_id}. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"An error occurred while deleting webhook ID {webhook_id}: {e}")

def delete_all_webhooks(API_USER_ID, API_SECRET_KEY):
    # Retrieve all webhooks
    webhooks = get_webhooks(API_USER_ID, API_SECRET_KEY)
    print(webhooks)
    if webhooks:
        for webhook in webhooks:
            webhook_id = webhook['id']
            delete_webhook(webhook_id)

# delete_all_webhooks(API_USER_ID, API_SECRET_KEY)

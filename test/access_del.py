import requests

ACCESS_TOKEN = "JE2QhB2yYMNyeQulrhtgsWrc01C6fcGOVpfygNcB"

BASE_URL = "https://acuityscheduling.com/api/v1/webhooks"

def get_webhooks():
    try:
        response = requests.get(
            BASE_URL,
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }
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
        delete_url = f"{BASE_URL}/{webhook_id}"
        response = requests.delete(
            delete_url,
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }
        )
        if response.status_code == 204:
            print(f"Webhook ID {webhook_id} deleted successfully.")
        else:
            print(f"Failed to delete webhook ID {webhook_id}. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"An error occurred while deleting webhook ID {webhook_id}: {e}")

def delete_all_webhooks():
    webhooks = get_webhooks()
    if webhooks:
        for webhook in webhooks:
            webhook_id = webhook['id']
            delete_webhook(webhook_id)

delete_all_webhooks()

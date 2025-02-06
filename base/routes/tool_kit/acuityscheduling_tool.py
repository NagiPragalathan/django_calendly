import requests

def create_webhooks(webhook_configs, acuity_user_id, acuity_api_key):
    """
    Create webhooks for specified events with their corresponding target URLs.

    Args:
        webhook_configs (list): A list of dictionaries with "event" and "target" keys.
        acuity_user_id (str): The Acuity Scheduling API user ID.
        acuity_api_key (str): The Acuity Scheduling API key.

    Returns:
        bool: True if all webhooks are created successfully, False otherwise.
    """
    # Base URL for the Acuity Scheduling API
    BASE_URL = "https://acuityscheduling.com/api/v1"
    WEBHOOK_ENDPOINT = f"{BASE_URL}/webhooks"

    all_success = True

    # Iterate over the webhook configurations and create a webhook for each
    for config in webhook_configs:
        webhook_data = {
            "target": config["target"],
            "event": config["event"]
        }
        # Make a POST request to create the webhook
        response = requests.post(
            WEBHOOK_ENDPOINT,
            json=webhook_data,
            auth=(acuity_user_id, acuity_api_key)
        )
        # Check the response
        if response.status_code == 200 or response.status_code == 201:
            print(f"Webhook for {config['event']} created successfully!")
        else:
            print(f"Failed to create webhook for {config['event']}.")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
            all_success = False

    return all_success


def get_webhooks_with_ids(user_id, api_key):
    """
    Retrieve the list of webhook IDs and target URLs from the Acuity Scheduling API.

    Parameters:
        user_id (str): The Acuity Scheduling user ID.
        api_key (str): The Acuity Scheduling API key.

    Returns:
        list: A list of [id, target] pairs if successful, otherwise an empty list.
    """
    # Base URL for the Acuity Scheduling API
    base_url = "https://acuityscheduling.com/api/v1"
    # Endpoint for retrieving webhooks
    webhooks_endpoint = f"{base_url}/webhooks"

    try:
        # Make a GET request to retrieve the list of webhooks
        response = requests.get(webhooks_endpoint, auth=(user_id, api_key))
        
        # Check the response status code
        if response.status_code == 200:
            webhooks = response.json()
            # Extract the IDs and target URLs from the webhooks
            webhook_list = [[webhook['id'], webhook['target']] for webhook in webhooks]
            return webhook_list
        else:
            print("Failed to retrieve webhooks.")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
            return []
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return []
    
def delete_webhooks(webhook_id, user_id, api_key):
    """
    Delete webhooks from the Acuity Scheduling API.

    Parameters:
        webhook_id (str | list): A single webhook ID (string) or a list of webhook IDs to delete.
        user_id (str): The Acuity Scheduling user ID.
        api_key (str): The Acuity Scheduling API key.

    Returns:
        dict: A dictionary with the webhook ID as the key and the deletion status as the value.
    """
    # Base URL for the Acuity Scheduling API
    base_url = "https://acuityscheduling.com/api/v1"
    results = {}
    delete_webhook_endpoint = f"{base_url}/webhooks/{webhook_id}"
    try:
        # Make a DELETE request to remove the webhook
        response = requests.delete(delete_webhook_endpoint, auth=(user_id, api_key))
        # Check the response
        if response.status_code in [200, 204]:
            results[webhook_id] = "Successfully deleted"
            print(f"Webhook with ID {webhook_id} removed successfully!")
        else:
            results[webhook_id] = f"Failed to delete - Status Code: {response.status_code}"
            print(f"Failed to remove webhook with ID {webhook_id}.")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
    except requests.RequestException as e:
        results[webhook_id] = f"Error occurred: {e}"
        print(f"An error occurred while deleting webhook with ID {webhook_id}: {e}")
    return results
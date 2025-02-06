import requests

# Acuity Scheduling API credentials
ACUITY_USER_ID = "15632977"  # Replace with your user ID
ACUITY_API_KEY = "0000b6ceb812a72dde36b6c41a8b057f"  # Replace with your API key

# Base URL for the Acuity Scheduling API
BASE_URL = "https://acuityscheduling.com/api/v1"

# Endpoint for creating webhooks
WEBHOOK_ENDPOINT = f"{BASE_URL}/webhooks"

# List of webhook events and their corresponding target URLs
webhook_configs = [
    {"event": "appointment.rescheduled", "target": "https://yourwebhookendpoint.com/rescheduled"},
    {"event": "appointment.scheduled", "target": "https://yourwebhookendpoint.com/scheduled"},
    {"event": "appointment.canceled", "target": "https://yourwebhookendpoint.com/canceled"},
]

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
        auth=(ACUITY_USER_ID, ACUITY_API_KEY)
    )
    # Check the response
    if response.status_code == 200 or response.status_code == 201:
        print(f"Webhook for {config['event']} created successfully!")
        print("Response:", response.json())
    else:
        print(f"Failed to create webhook for {config['event']}.")
        print("Status Code:", response.status_code)
        print("Response:", response.text)

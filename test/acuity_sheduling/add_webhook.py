import requests

# Acuity Scheduling API credentials
ACUITY_USER_ID = "15632977"  # Replace with your user ID
ACUITY_API_KEY = "0000b6ceb812a72dde36b6c41a8b057f"  # Replace with your API key

# Base URL for the Acuity Scheduling API
BASE_URL = "https://acuityscheduling.com/api/v1"

# Endpoint for creating webhooks
WEBHOOK_ENDPOINT = f"{BASE_URL}/webhooks"

# Webhook payload
webhook_data = {
    "target": "https://django-acuity-scheduling.vercel.app/acuity-webhook/create-meeting/",
    "event": "appointment.scheduled"
}

# Make a POST request to create the webhook
response = requests.post(
    WEBHOOK_ENDPOINT,
    json=webhook_data,
    auth=(ACUITY_USER_ID, ACUITY_API_KEY)
)

# Check the response
if response.status_code == 200 or response.status_code == 201:
    print("Webhook created successfully!")
    print("Response:", response.json())
else:
    print("Failed to create webhook.")
    print("Status Code:", response.status_code)
    print("Response:", response.text)

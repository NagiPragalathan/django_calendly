import requests

# Acuity Scheduling API credentials
ACUITY_USER_ID = "15632977"  # Replace with your user ID
ACUITY_API_KEY = "0000b6ceb812a72dde36b6c41a8b057f"  # Replace with your API key

# Base URL for the Acuity Scheduling API
BASE_URL = "https://acuityscheduling.com/api/v1"

# Endpoint for retrieving webhooks
WEBHOOKS_ENDPOINT = f"{BASE_URL}/webhooks"

# Make a GET request to retrieve the list of webhooks
response = requests.get(
    WEBHOOKS_ENDPOINT,
    auth=(ACUITY_USER_ID, ACUITY_API_KEY)
)

# Check the response
if response.status_code == 200:
    print("Webhooks retrieved successfully!")
    webhooks = response.json()
    for webhook in webhooks:
        print(f"ID: {webhook['id']}, Event: {webhook['event']}, Target: {webhook['target']}")
else:
    print("Failed to retrieve webhooks.")
    print("Status Code:", response.status_code)
    print("Response:", response.text)

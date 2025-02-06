import requests

# Acuity Scheduling API credentials
ACUITY_USER_ID = "15632977"  # Replace with your user ID
ACUITY_API_KEY = "0000b6ceb812a72dde36b6c41a8b057f"  # Replace with your API key

# Base URL for the Acuity Scheduling API
BASE_URL = "https://acuityscheduling.com/api/v1"

# Make a DELETE request to remove the webhook


for i in ['846354', '846353', '846352']:
    # Endpoint for deleting the webhook
    DELETE_WEBHOOK_ENDPOINT = f"{BASE_URL}/webhooks/{i}"

    response = requests.delete(
        DELETE_WEBHOOK_ENDPOINT,
        auth=(ACUITY_USER_ID, ACUITY_API_KEY)
    )

    # Check the response
    if response.status_code == 200 or response.status_code == 204:
        print(f"Webhook with ID {i} removed successfully!")
    else:
        print("Failed to remove webhook.")
        print("Status Code:", response.status_code)
        print("Response:", response.text)

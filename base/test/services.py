import requests
from requests.auth import HTTPBasicAuth

# Replace with your actual credentials
USER_ID = '15632977'
API_KEY = '0000b6ceb812a72dde36b6c41a8b057f'

def fetch_appointment_types():
    """
    Fetch all appointment types and generate scheduling links.
    """
    base_url = "https://acuityscheduling.com/api/v1"
    appointment_types_endpoint = f"{base_url}/appointment-types"

    # Authentication using USER_ID and API_KEY
    auth = HTTPBasicAuth(USER_ID, API_KEY)

    try:
        print(f"Requesting appointment types from {appointment_types_endpoint}...")
        response = requests.get(appointment_types_endpoint, auth=auth)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse JSON response
        appointment_types = response.json()

        # Generate links for each appointment type
        links = [
            {
                "name": appt_type.get("name"),
                "duration": appt_type.get("duration"),
                "link": f"https://app.acuityscheduling.com/schedule.php?owner={USER_ID}&appointmentType={appt_type.get('id')}"
            }
            for appt_type in appointment_types
        ]

        return links

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return []

# Fetch and display links
links = fetch_appointment_types()
if links:
    print("Generated Appointment Links:")
    for link in links:
        print(f"Name: {link['name']}, Duration: {link['duration']} minutes, Link: {link['link']}")
else:
    print("No appointment types found.")




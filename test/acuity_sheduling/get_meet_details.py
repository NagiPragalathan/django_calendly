import requests

# Acuity Scheduling API credentials
API_USER_ID = "15632977"
API_KEY = "0000b6ceb812a72dde36b6c41a8b057f"

# Base URL for Acuity API
BASE_URL = "https://acuityscheduling.com/api/v1"

# Function to fetch appointment details
def get_appointment_details(appointment_id):
    try:
        url = f"{BASE_URL}/appointments/{appointment_id}"
        response = requests.get(url, auth=(API_USER_ID, API_KEY))

        if response.status_code == 200:
            appointment_data = response.json()
            print("Appointment Details:")
            print(appointment_data)

            # Extract candidate name and appointment type ID
            candidate_name = f"{appointment_data.get('firstName', '')} {appointment_data.get('lastName', '')}"
            appointment_type_id = appointment_data.get("appointmentTypeID")
            type_name = appointment_data.get("type", {})
            print(f"Candidate Name: {candidate_name}")
            print(f"Appointment Type Name: {type_name}")
            print(f"Appointment Type ID: {appointment_type_id}")

        else:
            print(f"Failed to fetch appointment details: {response.status_code}")
            print(response.json())
    except Exception as e:
        print(f"Error: {e}")

# Function to fetch appointment type details
def get_appointment_type_details(appointment_type_id):
    try:
        url = f"{BASE_URL}/appointment-types/{appointment_type_id}"
        response = requests.get(url, auth=(API_USER_ID, API_KEY))

        if response.status_code == 200:
            appointment_type_data = response.json()
            print("Appointment Type Details:")
            print(appointment_type_data)

            # Extract and display the appointment type name
            appointment_type_name = appointment_type_data.get("name", "Unknown")
            print(f"Appointment Type Name: {appointment_type_name}")
        else:
            print(f"Failed to fetch appointment type details: {response.status_code}")
            print(response.json())
    except Exception as e:
        print(f"Error: {e}")

# Main function
def main():
    # Extracted from the webhook payload
    appointment_id = 1406861328  # Replace with the actual appointment ID from the webhook

    # Fetch appointment details
    get_appointment_details(appointment_id)

if __name__ == "__main__":
    main()

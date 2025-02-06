import requests

# Zoho CRM API Credentials
CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
REFRESH_TOKEN = "1000.57c85253d1aa2d45b3f497082a83127a.611fc6edf04a30c1cee5e1b6c3d85620"

# Zoho API URLs
TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
BASE_URL = "https://www.zohoapis.com/crm/v2"

def get_access_token():
    """Fetch a new access token using the refresh token."""
    payload = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(TOKEN_URL, data=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching access token: {e}")
        return None

def search_email(access_token, email, module):
    """Search for an email in the specified module (Leads or Contacts)."""
    url = f"{BASE_URL}/{module}/search"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    params = {"email": email}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 204:
            return None  # No records found
        response.raise_for_status()
        data = response.json()
        
        if "data" in data:
            return data["data"][0]  # Return first matching record
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error searching {module}: {e}")
        return None

def create_new_record(access_token, module, user_data):
    """Create a new record in the specified module."""
    url = f"{BASE_URL}/{module}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    payload = {"data": [user_data]}  # Zoho API requires data inside a list

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if "data" in data and data["data"][0].get("code") == "SUCCESS":
            return data["data"][0]["details"]["id"]  # Return the created user ID
        else:
            print(f"❌ Failed to create record. Response: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating record in {module}: {e}")
        return None

def check_and_add_email(user_data, module):
    """Check if the email exists, if not, create a new record."""
    access_token = get_access_token()
    
    if not access_token:
        print("❌ Unable to continue without a valid access token.")
        return

    email = user_data.get("Email")
    
    # Check if the email already exists
    existing_user = search_email(access_token, email, module)
    
    if existing_user:
        print(f"✅ Email '{email}' already exists in {module}. User ID: {existing_user['id']}")
        return existing_user["id"]
    else:
        print(f"⚠️ Email '{email}' not found in {module}. Creating new record...")

        # Create a new record
        new_user_id = create_new_record(access_token, module, user_data)
        if new_user_id:
            print(f"✅ New user created in {module} with ID: {new_user_id}")
        return new_user_id

# Example user data from Acuity Scheduling
user_data = {
    "First_Name": "Nagi",
    "Last_Name": "Pragalathan",
    "Email": "nagipragalathamm@gmail.com",
    "Phone": "7401268095",
    "Lead_Source": "Acuity Scheduling",
    "Company": "Real Estate",
    "Description": "Real Estate Consultation Appointment",
    "Annual_Revenue": "2000.00"
}

# Example usage
module_to_check = input("Enter module (Leads or Contacts): ").strip().capitalize()
check_and_add_email(user_data, module_to_check)

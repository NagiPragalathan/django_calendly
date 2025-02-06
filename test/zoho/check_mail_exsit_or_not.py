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
        response.raise_for_status()  # Raise an error for bad HTTP responses (4xx or 5xx)
        data = response.json()
        
        if "access_token" in data:
            return data["access_token"]
        else:
            print(f"❌ Failed to get access token. Response: {data}")
            return None
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
            print(f"⚠️ No data found for email: {email} in {module}.")
            return None
        response.raise_for_status()  # Raise an error for bad HTTP responses

        try:
            data = response.json()
            if "data" in data:
                return data["data"]
            else:
                print(f"⚠️ No matching record found in {module}. Response: {data}")
                return None
        except requests.exceptions.JSONDecodeError:
            print(f"❌ Failed to parse JSON response. Raw Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error while querying {module}: {e}")
        return None

def check_email_exists(email, module):
    """Check if an email exists in the specified module (Leads or Contacts)."""
    access_token = get_access_token()
    
    if not access_token:
        print("❌ Unable to continue without a valid access token.")
        return

    if module not in ["Leads", "Contacts"]:
        print("❌ Invalid module. Please enter either 'Leads' or 'Contacts'.")
        return

    result = search_email(access_token, email, module)
    if result:
        print(f"✅ Email '{email}' found in {module}.")
    else:
        print(f"❌ Email '{email}' not found in {module}.")

# Example usage: User Input
email_to_check = input("Enter the email to search: ").strip()
module_to_check = input("Enter module (Leads or Contacts): ").strip().capitalize()

check_email_exists(email_to_check, module_to_check)

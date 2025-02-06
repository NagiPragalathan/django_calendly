import requests

# Endpoint URL with specific phone number
url = "https://live-mt-server.wati.io/326166/api/v1/getMessages/919692397619"

# Headers
headers = {
    "accept": "*/*",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIwZjdlMjEzMS1kMDVhLTQ0YjMtYjMzMC0xMzk2ZTczMWYzN2IiLCJ1bmlxdWVfbmFtZSI6InByZW1AeHRyYWN1dC5jb20iLCJuYW1laWQiOiJwcmVtQHh0cmFjdXQuY29tIiwiZW1haWwiOiJwcmVtQHh0cmFjdXQuY29tIiwiYXV0aF90aW1lIjoiMTEvMDYvMjAyNCAwOTozMDozNiIsInRlbmFudF9pZCI6IjMyNjE2NiIsImRiX25hbWUiOiJtdC1wcm9kLVRlbmFudHMiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJBRE1JTklTVFJBVE9SIiwiZXhwIjoyNTM0MDIzMDA4MDAsImlzcyI6IkNsYXJlX0FJIiwiYXVkIjoiQ2xhcmVfQUkifQ.zeK2divrIFx6dvIKMahkuMFWlK4XXx9Gmkp_0oVllvI"
}

# Make the GET request
response = requests.get(url, headers=headers)

# Check response status and print result
if response.status_code == 200:
    data = response.json()  # Parse JSON response
    print("Messages Data:", data)
else:
    print("Failed to retrieve messages:", response.status_code, response.text)

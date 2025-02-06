import requests
import pandas as pd
from datetime import datetime

# Endpoint URL with specific phone number
url = "https://live-mt-server.wati.io/326166/api/v1/getMessages/919692397619"

# Headers
headers = {
    "accept": "*/*",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIwZjdlMjEzMS1kMDVhLTQ0YjMtYjMzMC0xMzk2ZTczMWYzN2IiLCJ1bmlxdWVfbmFtZSI6InByZW1AeHRyYWN1dC5jb20iLCJuYW1laWQiOiJwcmVtQHh0cmFjdXQuY29tIiwiZW1haWwiOiJwcmVtQHh0cmFjdXQuY29tIiwiYXV0aF90aW1lIjoiMTEvMDYvMjAyNCAwOTozMDozNiIsInRlbmFudF9pZCI6IjMyNjE2NiIsImRiX25hbWUiOiJtdC1wcm9kLVRlbmFudHMiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJBRE1JTklTVFJBVE9SIiwiZXhwIjoyNTM0MDIzMDA4MDAsImlzcyI6IkNsYXJlX0FJIiwiYXVkIjoiQ2xhcmVfQUkifQ.zeK2divrIFx6dvIKMahkuMFWlK4XXx9Gmkp_0oVllvI"
}

# Make the GET request
response = requests.get(url, headers=headers)

# Check response status and process result
if response.status_code == 200:
    data = response.json()  # Parse JSON response
    messages = data.get('messages', {}).get('items', [])

    # Prepare data for Excel
    records = []
    for message in messages:
        record = {
            'Event Description': message.get('eventDescription', ''),
            'Text': message.get('text', ''),
            'Type': message.get('type', ''),
            'Owner': message.get('owner', ''),
            'Status': message.get('statusString', ''),
            'Actor': message.get('actor', ''),
            'Assignee': message.get('assignee', ''),
            'Created': message.get('created', ''),
            'Time': datetime.fromtimestamp(float(message['timestamp'])).strftime('%Y-%m-%d %H:%M:%S') if 'timestamp' in message else '',
            'Conversation ID': message.get('conversationId', ''),
            'Ticket ID': message.get('ticketId', ''),
            'Event Type': message.get('eventType', '')
        }
        records.append(record)

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Save to Excel
    output_path = 'messages_data.xlsx'
    df.to_excel(output_path, index=False)
    print("Messages data has been saved to messages_data.xlsx")
else:
    print("Failed to retrieve messages:", response.status_code, response.text)




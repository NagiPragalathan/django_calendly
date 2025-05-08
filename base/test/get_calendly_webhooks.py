import requests

url = "https://api.calendly.com/webhook_subscriptions"

# Replace this with your actual user URI
user_uri = "https://api.calendly.com/users/51521379-e318-4ff2-a52b-59865a2bfdb1"

querystring = {
    "organization": "https://api.calendly.com/organizations/3f0ebc83-99f6-4b0f-9d3a-ccf2df1f383f", 
    "count": "6", 
    "scope": "user",
    "user": user_uri  # Add the user parameter
}

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiSldUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzQ2Njg0ODI2LCJqdGkiOiI5NWFkMjlkZC0wMmQwLTRiMTYtOTRkMC0zNWE0OGQzMzk3ZjAiLCJ1c2VyX3V1aWQiOiJjZTc5Mzk0Ni00MmNlLTQ3MzUtODNkMS1iNGNlMDcxNTVmYmYiLCJhcHBfdWlkIjoibW1nekgzTUdIT2w0WHhTb19TMlJkODhOSGtRWE50cDJCQjFvQmNIdWVfcyIsImV4cCI6MTc0NjY5MjAyNn0.V0JLx_DcWBZ1d6gvM26hWYAjYS345BoMhH8ouGgz6Tzs9nthUIRVtupx4RvKO_Zd2Pz7RuPZLo2GwRfisgtQLA"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.text)

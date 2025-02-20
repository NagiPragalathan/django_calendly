import requests

url = "https://api.calendly.com/webhook_subscriptions"

# Replace this with your actual user URI
user_uri = "https://api.calendly.com/users/51521379-e318-4ff2-a52b-59865a2bfdb1"

querystring = {
    "organization": "https://api.calendly.com/organizations/3f0ebc83-99f6-4b0f-9d3a-ccf2df1f383f", 
    "count": "1", 
    "scope": "user",
    "user": user_uri  # Add the user parameter
}

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiSldUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzQwMDMyOTcwLCJqdGkiOiJkN2Y0MDUwMi01MzI0LTRmYmYtOWUxMC0wMWI3ZTBkNGQzZjUiLCJ1c2VyX3V1aWQiOiI1MTUyMTM3OS1lMzE4LTRmZjItYTUyYi01OTg2NWEyYmZkYjEiLCJhcHBfdWlkIjoibW1nekgzTUdIT2w0WHhTb19TMlJkODhOSGtRWE50cDJCQjFvQmNIdWVfcyIsImV4cCI6MTc0MDA0MDE3MH0.waIwdjVAjx8iYzPXuhXwwv-PfFBD48-nucuiyjI0d6hlojI00ECHcStLBGvEOEo6h4HlCMfFbWMzIqFnNL1b7g"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.text)

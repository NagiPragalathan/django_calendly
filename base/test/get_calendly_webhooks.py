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
    "Authorization": "Bearer eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiSldUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzQwMDQ2NzQ4LCJqdGkiOiJkZTVkYTY2Ny0yOTI3LTRjOWQtYTY1Ni1jZGFkNGZlOGRjZWMiLCJ1c2VyX3V1aWQiOiI1MTUyMTM3OS1lMzE4LTRmZjItYTUyYi01OTg2NWEyYmZkYjEiLCJhcHBfdWlkIjoibW1nekgzTUdIT2w0WHhTb19TMlJkODhOSGtRWE50cDJCQjFvQmNIdWVfcyIsImV4cCI6MTc0MDA1Mzk0OH0.tzFqZ_wxU3raR-KejWoV96g1vJ-tZP-dml3E4Wv3kN3DvOTMlBEhP23RcihW_0b_4GyRTo_i51jS5s66xZZwaA"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.text)

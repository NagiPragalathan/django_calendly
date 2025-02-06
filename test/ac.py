import requests

# Replace these values with your app's credentials
client_id = "xdzTMGcRRK2AoMj9"
client_secret = "MZPuZhB6HMI2A9VQY8YFySDyIyTRaAqZtKe1cEKB"
redirect_uri = "http://127.0.0.1:8000/callback"
auth_code = "MpOWqbDiuXCnVjfrpdGFuSdRQ4J2pTvJSX6UPVFv"

url = f'https://acuityscheduling.com/oauth2/authorize?response_type=code&scope=api-v1&client_id={client_id}&redirect_uri={redirect_uri}'
print(url)


# Exchange the authorization code for tokens
token_url = "https://acuityscheduling.com/oauth2/token"
data = {
    "client_id": client_id,
    "client_secret": client_secret,
    "redirect_uri": redirect_uri,
    "grant_type": "authorization_code",
    "code": auth_code,
}

response = requests.post(token_url, data=data)
if response.status_code == 200:
    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    print("Access Token:", access_token)
    print("Refresh Token:", refresh_token)
else:
    print("Error:", response.json())

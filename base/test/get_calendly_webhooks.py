import requests
import json
from typing import Dict, Any

def get_calendly_webhooks(access_token: str) -> Dict[str, Any]:
    """
    Retrieve all webhooks for the given Calendly access token.
    
    Args:
        access_token (str): The Calendly access token
        
    Returns:
        Dict[str, Any]: Response containing webhooks or error information
    """
    try:
        # API endpoint for webhooks
        url = "https://api.calendly.com/webhook_subscriptions"
        
        # Headers with authorization
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Make the GET request
        response = requests.get(url, headers=headers)
        
        # Check if request was successful
        if response.status_code == 200:
            webhooks = response.json()
            return {
                "success": True,
                "data": webhooks,
                "message": f"Found {len(webhooks.get('collection', []))} webhooks"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to get webhooks: {response.status_code}",
                "details": response.json()
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error occurred: {str(e)}"
        }

if __name__ == "__main__":
    # Your access token
    ACCESS_TOKEN = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiSldUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzM5NjEwODM0LCJqdGkiOiJhMzQ0YWM0MS03YTMxLTQyYjMtYmU3YS1iZjE1N2MxNTk1NzQiLCJ1c2VyX3V1aWQiOiI0NWQzOTEzZC00ZWVhLTRmZGYtOTQ1Zi0wNGUyZGUyYmNmZjYiLCJhcHBfdWlkIjoibW1nekgzTUdIT2w0WHhTb19TMlJkODhOSGtRWE50cDJCQjFvQmNIdWVfcyIsImV4cCI6MTczOTYxODAzNH0.BAU1DBbsRB1lC7Dgk8JxbdH816KtvCmWJqx85Yx6v64VMwsRuizo8T11agnY39YvF544_fIC4OR96h04Lv2Leg"
    
    # Get the webhooks
    result = get_calendly_webhooks(ACCESS_TOKEN)
    
    # Print results in a formatted way
    if result["success"]:
        print("\nSuccessfully retrieved webhooks:")
        webhooks = result["data"]["collection"]
        
        if not webhooks:
            print("No webhooks found.")
        else:
            for webhook in webhooks:
                print("\nWebhook Details:")
                print(f"URI: {webhook.get('uri')}")
                print(f"Callback URL: {webhook.get('callback_url')}")
                print(f"Created At: {webhook.get('created_at')}")
                print(f"State: {webhook.get('state')}")
                print(f"Events: {', '.join(webhook.get('events', []))}")
                print(f"Scope: {webhook.get('scope')}")
                print(f"Organization: {webhook.get('organization')}")
                print(f"User: {webhook.get('user')}")
                print("-" * 50)
    else:
        print("\nError retrieving webhooks:")
        print(f"Error message: {result.get('error')}")
        if result.get('details'):
            print(f"Details: {json.dumps(result['details'], indent=2)}")
import requests
from django.conf import settings
from typing import List, Dict, Union, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from base.models import CalendlyCredentials
from django.core.exceptions import ObjectDoesNotExist

class CalendlyWebhookManager:
    """Manages Calendly webhooks for the application."""
    
    def __init__(self, access_token: str):
        self.base_url = "https://api.calendly.com/webhook_subscriptions"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.organization_url = None
        self.user_url = None
        self._set_organization_and_user()

    def _set_organization_and_user(self):
        """Fetch and set the organization and user URLs."""
        try:
            response = requests.get(
                "https://api.calendly.com/users/me",
                headers=self.headers
            )
            if response.status_code == 200:
                user_data = response.json().get('resource', {})
                self.organization_url = user_data.get('current_organization')
                self.user_url = user_data.get('uri')
        except requests.RequestException as e:
            print(f"Error fetching organization and user: {e}")

    def create_webhook(self, url: str, events: List[str], scope: str = "user") -> Dict:
        """
        Create a new webhook subscription.

        Args:
            url (str): The callback URL where events will be sent
            events (List[str]): List of events to subscribe to
            scope (str): Scope of the webhook ('user' or 'organization')

        Returns:
            Dict: Response from the API or error information
        """
        if not self.organization_url:
            return {"success": False, "error": "Organization URL not found"}

        payload = {
            "url": url,
            "events": events,
            "organization": self.organization_url,
            "scope": scope
        }

        # Add user URI for user-scoped webhooks
        if scope == "user" and self.user_url:
            payload["user"] = self.user_url

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                return {
                    "success": True,
                    "data": response.json().get('resource', {}),
                    "message": "Webhook created successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create webhook: {response.text}",
                    "status_code": response.status_code
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

    def list_webhooks(self, scope: str = "user") -> Dict:
        """List all webhook subscriptions."""
        try:
            params = {
                "organization": self.organization_url,
                "scope": scope
            }
            if scope == "user" and self.user_url:
                params["user"] = self.user_url

            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json().get('collection', [])
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to fetch webhooks: {response.text}",
                    "status_code": response.status_code
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

    def delete_webhook(self, webhook_uuid: str) -> Dict:
        """Delete a specific webhook subscription."""
        try:
            response = requests.delete(
                f"{self.base_url}/{webhook_uuid}",
                headers=self.headers
            )

            if response.status_code == 204:
                return {
                    "success": True,
                    "message": f"Webhook {webhook_uuid} deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to delete webhook: {response.status_code}",
                    "status_code": response.status_code
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

    def update_webhook(self, webhook_id: str, url: Optional[str] = None, 
                      events: Optional[List[str]] = None) -> Dict:
        """
        Update an existing webhook subscription.

        Args:
            webhook_id (str): The UUID of the webhook to update
            url (Optional[str]): New callback URL
            events (Optional[List[str]]): New list of events to subscribe to

        Returns:
            Dict: Updated webhook information or error details
        """
        payload = {}
        if url:
            payload['url'] = url
        if events:
            payload['events'] = events

        try:
            response = requests.patch(
                f"{self.base_url}/{webhook_id}",
                headers=self.headers,
                json=payload
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "message": f"Webhook {webhook_id} updated successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to update webhook: {response.text}",
                    "status_code": response.status_code
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

class CalendlyTokenManager:
    """Manages Calendly OAuth tokens with automatic refresh."""
    
    def __init__(self):
        self.token_url = "https://auth.calendly.com/oauth/token"
        self.client_id = settings.CALENDLY_CLIENT_ID
        self.client_secret = settings.CALENDLY_CLIENT_SECRET

    def get_valid_access_token(self, credential_id, user_email):
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            credential_id (str): The unique_id of the CalendlyCredentials
            user_email (str): The user's email address
            
        Returns:
            tuple: (access_token, error_message)
        """
        cache_key = f'calendly_token_{credential_id}'
        cached_token = cache.get(cache_key)
        
        if cached_token:
            return cached_token, None

        try:
            credentials = CalendlyCredentials.objects.get(
                unique_id=credential_id,
                email=user_email
            )

            # Check if token needs refresh
            if credentials.is_token_expired():
                refresh_result = self.refresh_token(credentials)
                if not refresh_result['success']:
                    return None, refresh_result['error']
                credentials = refresh_result['credentials']

            # Cache the valid token
            cache.set(cache_key, credentials.access_token, timeout=3300)  # Cache for 55 minutes
            return credentials.access_token, None

        except ObjectDoesNotExist:
            return None, "Credentials not found"
        except Exception as e:
            return None, f"Error getting access token: {str(e)}"

    def refresh_token(self, credentials):
        """
        Refresh the access token using the refresh token.
        
        Args:
            credentials (CalendlyCredentials): The credentials object to refresh
            
        Returns:
            dict: Result of the refresh operation
        """
        try:
            response = requests.post(
                self.token_url,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': credentials.refresh_token
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )

            if response.status_code == 200:
                token_data = response.json()
                
                # Update credentials
                credentials.access_token = token_data['access_token']
                if 'refresh_token' in token_data:
                    credentials.refresh_token = token_data['refresh_token']
                
                # Update expiration
                credentials.update_token_expiration(token_data.get('expires_in', 3600))
                credentials.save()

                return {
                    'success': True,
                    'credentials': credentials
                }
            else:
                return {
                    'success': False,
                    'error': f"Token refresh failed: {response.status_code} - {response.text}"
                }

        except requests.RequestException as e:
            return {
                'success': False,
                'error': f"Token refresh request failed: {str(e)}"
            }

def setup_calendly_webhooks(credential_id, user_email, base_webhook_url):
    """Set up Calendly webhooks with proper scoping."""
    token_manager = CalendlyTokenManager()
    access_token, error = token_manager.get_valid_access_token(credential_id, user_email)
    
    if error:
        return {'success': False, 'error': error}

    webhook_manager = CalendlyWebhookManager(access_token)
    
    # Define events and their scopes
    webhook_configs = [
        {
            "scope": "user",
            "events": [
                "invitee.created",
                "invitee.canceled",
                "invitee.rescheduled",
                "invitee_no_show.created",
                "invitee_no_show.deleted"
            ]
        },
        {
            "scope": "organization",
            "events": [
                "routing_form_submission.created"
            ]
        }
    ]

    results = []
    for config in webhook_configs:
        webhook_url = f"{base_webhook_url.rstrip('/')}/calendly-webhook/{credential_id}/{config['scope']}/"
        result = webhook_manager.create_webhook(
            url=webhook_url,
            events=config['events'],
            scope=config['scope']
        )
        results.append(result)

    # Return success only if all webhooks were created successfully
    if all(result['success'] for result in results):
        return {
            'success': True,
            'message': 'All webhooks created successfully',
            'data': results
        }
    else:
        return {
            'success': False,
            'error': 'Some webhooks failed to create',
            'data': results
        }

def cleanup_webhooks(credential_id, user_email):
    """
    Clean up all webhooks for a given credential.
    
    Args:
        credential_id (str): The unique_id of the CalendlyCredentials
        user_email (str): The user's email address
        
    Returns:
        dict: Cleanup results
    """
    token_manager = CalendlyTokenManager()
    access_token, error = token_manager.get_valid_access_token(credential_id, user_email)
    
    if error:
        return {
            'success': False,
            'error': error
        }

    webhook_manager = CalendlyWebhookManager(access_token)
    return webhook_manager.cleanup_webhooks()

def create_webhooks(webhook_configs, acuity_user_id, acuity_api_key):
    """
    Create webhooks for specified events with their corresponding target URLs.

    Args:
        webhook_configs (list): A list of dictionaries with "event" and "target" keys.
        acuity_user_id (str): The Acuity Scheduling API user ID.
        acuity_api_key (str): The Acuity Scheduling API key.

    Returns:
        bool: True if all webhooks are created successfully, False otherwise.
    """
    # Base URL for the Acuity Scheduling API
    BASE_URL = "https://acuityscheduling.com/api/v1"
    WEBHOOK_ENDPOINT = f"{BASE_URL}/webhooks"

    all_success = True

    # Iterate over the webhook configurations and create a webhook for each
    for config in webhook_configs:
        webhook_data = {
            "target": config["target"],
            "event": config["event"]
        }
        # Make a POST request to create the webhook
        response = requests.post(
            WEBHOOK_ENDPOINT,
            json=webhook_data,
            auth=(acuity_user_id, acuity_api_key)
        )
        # Check the response
        if response.status_code == 200 or response.status_code == 201:
            print(f"Webhook for {config['event']} created successfully!")
        else:
            print(f"Failed to create webhook for {config['event']}.")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
            all_success = False

    return all_success


def get_webhooks_with_ids(user_id, api_key):
    """
    Retrieve the list of webhook IDs and target URLs from the Acuity Scheduling API.

    Parameters:
        user_id (str): The Acuity Scheduling user ID.
        api_key (str): The Acuity Scheduling API key.

    Returns:
        list: A list of [id, target] pairs if successful, otherwise an empty list.
    """
    # Base URL for the Acuity Scheduling API
    base_url = "https://acuityscheduling.com/api/v1"
    # Endpoint for retrieving webhooks
    webhooks_endpoint = f"{base_url}/webhooks"

    try:
        # Make a GET request to retrieve the list of webhooks
        response = requests.get(webhooks_endpoint, auth=(user_id, api_key))
        
        # Check the response status code
        if response.status_code == 200:
            webhooks = response.json()
            # Extract the IDs and target URLs from the webhooks
            webhook_list = [[webhook['id'], webhook['target']] for webhook in webhooks]
            return webhook_list
        else:
            print("Failed to retrieve webhooks.")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
            return []
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return []
    
def delete_webhooks(webhook_id, user_id, api_key):
    """
    Delete webhooks from the Acuity Scheduling API.

    Parameters:
        webhook_id (str | list): A single webhook ID (string) or a list of webhook IDs to delete.
        user_id (str): The Acuity Scheduling user ID.
        api_key (str): The Acuity Scheduling API key.

    Returns:
        dict: A dictionary with the webhook ID as the key and the deletion status as the value.
    """
    # Base URL for the Acuity Scheduling API
    base_url = "https://acuityscheduling.com/api/v1"
    results = {}
    delete_webhook_endpoint = f"{base_url}/webhooks/{webhook_id}"
    try:
        # Make a DELETE request to remove the webhook
        response = requests.delete(delete_webhook_endpoint, auth=(user_id, api_key))
        # Check the response
        if response.status_code in [200, 204]:
            results[webhook_id] = "Successfully deleted"
            print(f"Webhook with ID {webhook_id} removed successfully!")
        else:
            results[webhook_id] = f"Failed to delete - Status Code: {response.status_code}"
            print(f"Failed to remove webhook with ID {webhook_id}.")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
    except requests.RequestException as e:
        results[webhook_id] = f"Error occurred: {e}"
        print(f"An error occurred while deleting webhook with ID {webhook_id}: {e}")
    return results
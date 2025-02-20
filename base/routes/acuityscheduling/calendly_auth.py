import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from base.models import CalendlyCredentials
from uuid import UUID
from base.routes.tool_kit.calendly_tool import CalendlyWebhookManager

def calendly_auth(request, credential_id):
    """Step 1: Redirect user to Calendly's OAuth authorization page."""
    if isinstance(credential_id, UUID):
        credential_id = str(credential_id)

    # Store credential ID in the session before redirecting
    request.session['credential_id'] = credential_id
    request.session.modified = True  # Ensure session updates are committed

    print(f"✅ Storing credential_id in session: {credential_id}",  "session:", request.session['credential_id'])

    # Generate the authorization URL
    auth_url = f"https://auth.calendly.com/oauth/authorize"
    redirect_url = f"{auth_url}?client_id={settings.CALENDLY_CLIENT_ID}&response_type=code&redirect_uri={settings.CALENDLY_REDIRECT_URI}"
    
    print(f"✅ Redirecting to: {redirect_url}")
    return redirect(redirect_url)

def calendly_callback(request):
    """Step 2: Handle OAuth callback and set up webhooks."""
    try:
        code = request.GET.get('code')

        # Retrieve credential_id from the session
        credential_id = request.session.get('credential_id')

        # Debugging: Print session data to track credential_id
        print(f"🔍 Retrieved credential_id from session: {credential_id}")
        print(f"📌 All session data: {dict(request.session)}")

        if not code:
            return JsonResponse({'error': 'Authorization code not received.'}, status=400)

        if not credential_id:
            return JsonResponse({'error': 'Credential ID not found in session.'}, status=400)

        # Convert credential_id back to UUID
        try:
            credential_id = UUID(credential_id)
            print(f"🔄 Converted credential_id to UUID: {credential_id}")
        except ValueError:
            return JsonResponse({'error': 'Invalid credential ID format.'}, status=400)

        # Exchange code for tokens
        token_url = 'https://auth.calendly.com/oauth/token'
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': settings.CALENDLY_CLIENT_ID,
            'client_secret': settings.CALENDLY_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.CALENDLY_REDIRECT_URI,
        }

        token_response = requests.post(token_url, data=token_data)

        if token_response.status_code == 200:
            tokens = token_response.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')

            print(f"✅ Tokens received. Access Token: {access_token}, Refresh Token: {refresh_token}")

            # Verify credential_id matches an existing object
            try:
                credential = CalendlyCredentials.objects.get(unique_id=credential_id)
                credential.access_token = access_token
                credential.refresh_token = refresh_token
                credential.save()

                print(f"✅ Tokens saved for credential ID: {credential_id}")

                # Verify token storage immediately after saving
                credential.refresh_from_db()
                if not credential.access_token:
                    raise Exception("⚠️ Failed to save access token")

                # Set up webhooks
                webhook_manager = CalendlyWebhookManager(access_token)

                # First, cleanup any existing webhooks
                existing_webhooks = webhook_manager.list_webhooks()
                if existing_webhooks.get('success'):
                    for webhook in existing_webhooks.get('data', []):
                        webhook_uuid = webhook['uri'].split('/')[-1]
                        webhook_manager.delete_webhook(webhook_uuid)

                # Define webhook configurations
                webhook_configs = [
                    {
                        "scope": "user",
                        "events": [
                            "invitee.created",
                            "invitee.canceled",
                            "invitee_no_show.created",
                            "invitee_no_show.deleted"
                        ],
                        "target": f"{settings.HOSTED_CALENDLY_CLIENT_ID}/calendly-webhook/meeting/{credential_id}/{request.user.id}/"
                    }
                ]

                # Create new webhooks
                webhook_results = []
                for config in webhook_configs:
                    result = webhook_manager.create_webhook(
                        url=config['target'],
                        events=config['events'],
                        scope=config['scope']
                    )
                    webhook_results.append(result)
                    print(f"✅ Webhook created for {config['scope']}: {result}")

                # Check webhook creation results
                webhook_status = 'success'
                if not all(result.get('success') for result in webhook_results):
                    failed_webhooks = [
                        result.get('error')
                        for result in webhook_results
                        if not result.get('success')
                    ]
                    print(f"⚠️ Warning: Some webhooks failed to create: {failed_webhooks}")
                    webhook_status = 'partial'

                return JsonResponse({
                    'status': 'success',
                    'message': 'Authentication successful and webhooks created',
                    'webhook_status': webhook_status,
                    'token_status': 'Tokens stored successfully',
                    'credential_id': str(credential_id)
                })

            except CalendlyCredentials.DoesNotExist:
                print(f"❌ No credential found with ID: {credential_id}")
                return JsonResponse({'error': f'No credential found with ID: {credential_id}'}, status=404)
            except Exception as e:
                print(f"❌ Error saving tokens or creating webhooks: {str(e)}")
                return JsonResponse({'error': f'Error saving tokens or creating webhooks: {str(e)}'}, status=500)

        else:
            print("❌ Token response error:", token_response.json())
            return JsonResponse({
                'error': 'Failed to get access token',
                'details': token_response.json()
            }, status=400)

    except Exception as e:
        print(f"❌ Error in calendly_callback: {str(e)}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

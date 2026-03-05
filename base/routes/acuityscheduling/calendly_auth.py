import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
from base.models import CalendlyCredentials
from uuid import UUID
from base.routes.tool_kit.calendly_tool import CalendlyWebhookManager
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from base.routes.tool_kit.zoho_tool import ensure_field_exists

@login_required
def calendly_auth(request, credential_id):
    """Step 1: Redirect user to Calendly's OAuth authorization page."""
    if isinstance(credential_id, UUID):
        credential_id = str(credential_id)

    # Dynamically build the redirect URI based on the current request domain
    redirect_uri = request.build_absolute_uri(reverse('calendly_callback'))
    
    # Include credential_id in the state parameter
    auth_url = "https://auth.calendly.com/oauth/authorize"
    auth_params = (
        f"client_id={settings.CALENDLY_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={redirect_uri}&"
        f"state={credential_id}"
    )
    
    redirect_url = f"{auth_url}?{auth_params}"
    
    print(f"✅ Redirecting to: {redirect_url}")
    return redirect(redirect_url)

def calendly_callback(request):
    """Step 2: Handle OAuth callback and set up webhooks."""
    try:
        code = request.GET.get('code')
        credential_id = request.GET.get('state')  # Get credential_id from state parameter

        print(f"🔍 Retrieved credential_id from state: {credential_id}")

        if not code:
            return JsonResponse({'error': 'Authorization code not received.'}, status=400)

        if not credential_id:
            return JsonResponse({'error': 'Credential ID not found in state parameter.'}, status=400)

        try:
            credential_id = UUID(credential_id)
            print(f"🔄 Converted credential_id to UUID: {credential_id}")
        except ValueError:
            return JsonResponse({'error': 'Invalid credential ID format.'}, status=400)

        # Dynamically build the same redirect URI for token exchange
        redirect_uri = request.build_absolute_uri(reverse('calendly_callback'))
        
        # Exchange code for tokens
        token_url = 'https://auth.calendly.com/oauth/token'
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': settings.CALENDLY_CLIENT_ID,
            'client_secret': settings.CALENDLY_CLIENT_SECRET,
            'code': code,
            'redirect_uri': redirect_uri,
        }

        token_response = requests.post(token_url, data=token_data)

        if token_response.status_code == 200:
            tokens = token_response.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')

            print(f"✅ Tokens received. Access Token: {access_token[:30]}...")

            try:
                # Update using unique_id instead of id
                credential = CalendlyCredentials.objects.filter(unique_id=credential_id).update(
                    access_token=access_token,
                    refresh_token=refresh_token
                )

                # Set up webhooks
                webhook_manager = CalendlyWebhookManager(access_token)
                
                # First, cleanup any existing webhooks
                existing_webhooks = webhook_manager.list_webhooks()
                if existing_webhooks.get('success'):
                    for webhook in existing_webhooks.get('data', []):
                        webhook_uuid = webhook['uri'].split('/')[-1]
                        webhook_manager.delete_webhook(webhook_uuid)

                # Ensure we have the correct user for the webhook target, even if session is lost
                current_user = request.user
                if not current_user.is_authenticated:
                    from django.contrib.auth.models import User
                    current_user = User.objects.filter(email=credential.email).first()

                # Step 3: Automatic Field Creation in Zoho (System Orchestration)
                if current_user:
                    try:
                        from base.routes.acuityscheduling.acuityscheduling_settings import INTEGRATION_FIELDS
                        for item in INTEGRATION_FIELDS:
                            ensure_field_exists(current_user, item['label'])
                        print("✅ Zoho Field Orchestration Complete.")
                    except Exception as fe:
                        print(f"⚠️ Field Orchestration Warning: {str(fe)}")

                # Define webhook configurations - Capture the current browser base URL
                base_url = request.build_absolute_uri('/')[:-1]
                
                credential = CalendlyCredentials.objects.filter(unique_id=credential_id).first()

                webhook_configs = [
                    {
                        "scope": "user",
                        "events": [
                            "invitee.created",
                            "invitee.canceled",
                            "invitee_no_show.created",
                            "invitee_no_show.deleted"
                        ],
                        "target": f"{base_url}/calendly-webhook/meeting/{str(credential.unique_id)}/{current_user.id if current_user else 'None'}/"
                    }
                ]

                # Create new webhooks
                webhook_results = []
                for config in webhook_configs:
                    try:
                        result = webhook_manager.create_webhook(
                            url=config['target'],
                            events=config['events'],
                            scope=config['scope']
                        )
                        webhook_results.append(result)
                        print(f"✅ Webhook created for {config['scope']}: {result}")
                    except Exception as webhook_error:
                        print(f"⚠️ Error creating webhook: {str(webhook_error)}")
                        webhook_results.append({"success": False, "error": str(webhook_error)})

                # Check webhook creation results
                webhook_status = 'success' if all(result.get('success') for result in webhook_results) else 'partial'

                if webhook_status == 'success':
                    messages.success(request, "Calendly account connected, Zoho fields verified, and webhooks established!")
                else:
                    messages.warning(request, "Account connected, but some webhooks or fields failed to initialize.")

                return redirect("list_credentials")

            except CalendlyCredentials.DoesNotExist:
                print(f"❌ No credential found with ID: {credential_id}")
                messages.error(request, f"No credential found with ID: {credential_id}")
                return redirect("list_credentials")
            except Exception as e:
                print(f"❌ Error saving tokens or creating webhooks: {str(e)}")
                messages.error(request, f"Connection failed: {str(e)}")
                return redirect("list_credentials")

        else:
            details = token_response.json()
            print("❌ Token response error:", details)
            messages.error(request, f"Failed to get access token: {details.get('error_description', 'Unknown error')}")
            return redirect("list_credentials")

    except Exception as e:
        print(f"❌ Error in calendly_callback: {str(e)}")
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect("list_credentials")

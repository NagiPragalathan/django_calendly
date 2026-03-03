from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import requests
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings

from base.models import CalendlyCredentials, PreFillMapping, ZohoToken
from base.routes.tool_kit.mongo_tool import store_image_in_mongodb
from base.routes.tool_kit.calendly_tool import create_webhooks, get_webhooks_with_ids, delete_webhooks, CalendlyWebhookManager
from base.routes.tool_kit.zoho_tool import ensure_field_exists, check_access_token_validity, get_access_token, get_module_fields
from Finalty.settings import CALENDLY_CUSTOM_FIELDS, CLIENT_ID, CLIENT_SECRET
from base.routes.tool_kit.calendly_tool import setup_calendly_webhooks, cleanup_webhooks
from django.http import JsonResponse
import json

base_webhook_events = "https://django-acuity-scheduling.vercel.app/"

@login_required
def list_credentials(request):

    credentials = CalendlyCredentials.objects.filter(email=request.user.email)
    
    # Get connection status for each credential
    for credential in credentials:
        credential.is_connected = bool(credential.refresh_token)
        credential.status_class = 'bg-green-400' if credential.is_connected else 'bg-red-400'
        credential.status_text = 'Connected' if credential.is_connected else 'Not Connected'

    return render(request, 'acuityscheduling/list_credentials.html', {
        'credentials': credentials,
        'user': request.user
    })

@login_required
def set_primary_credential(request, credential_id):
    """Designate a credential as the primary one for the user."""
    # Reset all primary flags for this user's email
    CalendlyCredentials.objects.filter(email=request.user.email).update(is_primary=False)
    
    # Set the chosen one as primary
    credential = get_object_or_404(CalendlyCredentials, unique_id=credential_id, email=request.user.email)
    credential.is_primary = True
    credential.save()
    
    # Also update active session
    request.session['active_calendly_id'] = str(credential.unique_id)
    
    messages.success(request, f"'{credential.company_name or credential.email}' set as Primary Account.")
    return redirect('list_credentials')

@login_required
def switch_active_account(request, credential_id):
    """Switch the current active account in session."""
    credential = get_object_or_404(CalendlyCredentials, unique_id=credential_id, email=request.user.email)
    request.session['active_calendly_id'] = str(credential.unique_id)
    messages.success(request, f"Switched to account: {credential.email}")
    
    return redirect(request.META.get('HTTP_REFERER', 'list_appointments'))

@login_required
def edit_credentials(request, credential_id):
    try:
        credential = CalendlyCredentials.objects.get(unique_id=credential_id, email=request.user.email)
    except CalendlyCredentials.DoesNotExist:
        return JsonResponse({'error': 'Credential not found.'}, status=404)

    # Fetch Lead fields for pre-fill mapping
    lead_fields = []
    zoho_token = ZohoToken.objects.filter(user=request.user).first()
    if zoho_token:
        access_token = zoho_token.access_token
        if not check_access_token_validity(access_token):
            access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
            ZohoToken.objects.filter(user=request.user).update(access_token=access_token)
        
        try:
            lead_data = get_module_fields(access_token, "Leads")
            if "fields" in lead_data:
                for f in lead_data["fields"]:
                    lead_fields.append({"api_name": f["api_name"], "label": f["field_label"]})
                lead_fields.sort(key=lambda x: x["label"])
        except: pass

    if request.method == 'POST':
        try:
            # Get form data
            image = request.FILES.get('image')
            company_name = request.POST.get('company_name')
            email_template = request.POST.get('email_template')
            
            # Handle Pre-fill Mappings (Dynamic Logic)
            PreFillMapping.objects.filter(user=request.user, calendly_account=credential).delete()
            q_keys = request.POST.getlist('q_key[]')
            z_fields = request.POST.getlist('z_field[]')
            for k, f in zip(q_keys, z_fields):
                if k and f:
                    PreFillMapping.objects.create(
                        user=request.user, 
                        calendly_account=credential, 
                        question_key=k, 
                        zoho_field_api_name=f
                    )

            if image:
                image_id = store_image_in_mongodb(image, request.user.email)
            else:
                image_id = credential.image_id

            # Update credentials in the database
            CalendlyCredentials.objects.filter(
                unique_id=credential_id, 
                email=request.user.email
            ).update(
                company_name=company_name,
                email_template=email_template,
                image_id=image_id
            )

            messages.success(request, f"Orchestration for '{company_name or credential.email}' updated successfully!")
            return redirect('list_credentials')

        except Exception as e:
            messages.error(request, f"Error updating hub logic: {str(e)}")
            return render(request, 'acuityscheduling/edit_credentials.html', {
                'credential': credential,
                'lead_fields': lead_fields,
                'prefill_mappings': PreFillMapping.objects.filter(user=request.user, calendly_account=credential),
                'error': str(e)
            })

    return render(request, 'acuityscheduling/edit_credentials.html', {
        'credential': credential,
        'lead_fields': lead_fields,
        'prefill_mappings': PreFillMapping.objects.filter(user=request.user, calendly_account=credential)
    })


@login_required
def create_credentials(request):
    if request.method == 'POST':
        try:
            image = request.FILES.get('image')
            company_name = request.POST.get('company_name')
            email_template = request.POST.get('email_template')
            access_token = request.POST.get('access_token')  # Get from OAuth flow
            refresh_token = request.POST.get('refresh_token')  # Get from OAuth flow
            
            #########################################################################################
            # Save image to MongoDB if provided
            #########################################################################################
            image_id = None
            if image:
                image_id = store_image_in_mongodb(image, request.user.email)
            
            #########################################################################################
            # Save credentials to the database
            #########################################################################################
            get_id = CalendlyCredentials.objects.create(
                email=request.user.email,
                image_id=image_id,
                company_name=company_name,
                email_template=email_template,
                access_token=access_token,
                refresh_token=refresh_token
            )

            messages.success(request, "Credentials created successfully!")
            return redirect('list_credentials')

        except Exception as e:
            print(f"Error creating credentials: {str(e)}")
            messages.error(request, f"Error creating credentials: {str(e)}")
            return render(request, 'acuityscheduling/create_credentials.html', {'error': str(e)})

    return render(request, 'acuityscheduling/create_credentials.html')


@login_required
def delete_credentials(request, credential_id):
    credential = get_object_or_404(CalendlyCredentials, unique_id=credential_id, email=request.user.email)
    credential.delete()
    messages.success(request, "Credentials deleted successfully!")
    return redirect('list_credentials')

def setup_webhook_view(request, credential_id):
    """View to handle webhook setup."""
    try:
        # Get base webhook URL from settings
        base_webhook_url = settings.BASE_WEBHOOK_URL

        # First cleanup any existing webhooks
        cleanup_result = cleanup_webhooks(credential_id, request.user.email)
        if not cleanup_result.get('success'):
            messages.warning(request, f"Webhook cleanup warning: {cleanup_result.get('error')}")

        # Setup new webhooks
        result = setup_calendly_webhooks(
            credential_id=credential_id,
            user_email=request.user.email,
            base_webhook_url=base_webhook_url
        )

        if result.get('success'):
            messages.success(request, "Webhooks setup successfully!")
            return JsonResponse({'status': 'success'})
        else:
            messages.error(request, f"Failed to setup webhooks: {result.get('error')}")
            return JsonResponse({
                'status': 'error',
                'message': result.get('error')
            }, status=400)

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
@login_required
def fetch_calendly_events(request, credential_id):
    """Fetch event types from Calendly for the given credential."""
    try:
        credential = CalendlyCredentials.objects.get(unique_id=credential_id, email=request.user.email)
        if not credential.access_token:
            return JsonResponse({'error': 'Hub not authenticated.'}, status=400)

        # Get the current user URI
        headers = {
            'Authorization': f'Bearer {credential.access_token}',
            'Content-Type': 'application/json'
        }
        user_res = requests.get('https://api.calendly.com/users/me', headers=headers)
        if user_res.status_code != 200:
            return JsonResponse({'error': 'Failed to fetch Calendly user data.'}, status=user_res.status_code)
        
        user_uri = user_res.json().get('resource', {}).get('uri')
        org_uri = user_res.json().get('resource', {}).get('current_organization')

        # Fetch event types
        params = {'user': user_uri}  # or organization=org_uri if preferred
        events_res = requests.get('https://api.calendly.com/event_types', headers=headers, params=params)
        
        if events_res.status_code != 200:
            return JsonResponse({'error': 'Failed to fetch event types.'}, status=events_res.status_code)
            
        return JsonResponse(events_res.json())

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

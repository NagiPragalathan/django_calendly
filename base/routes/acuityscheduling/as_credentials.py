from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import requests
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings

from base.models import CalendlyCredentials, PreFillMapping, ZohoToken, BookingEmailTemplate, Settings
from base.routes.tool_kit.mongo_tool import store_image_in_mongodb
from base.routes.tool_kit.calendly_tool import create_webhooks, get_webhooks_with_ids, delete_webhooks, CalendlyWebhookManager
from base.routes.tool_kit.zoho_tool import ensure_field_exists, check_access_token_validity, get_access_token, get_module_fields
from Finalty.settings import CALENDLY_CUSTOM_FIELDS, CLIENT_ID, CLIENT_SECRET
from base.routes.tool_kit.calendly_tool import setup_calendly_webhooks, cleanup_webhooks
from django.http import JsonResponse
import json


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

def _get_crm_fields_for_user(user):
    # Fetch modules from settings
    settings_obj = Settings.objects.filter(user=user).first()
    target_modules = [settings_obj.leads_to_store] if settings_obj else ["Leads", "Contacts"]
    
    # Fetch fields for pre-fill mapping
    module_fields = {m: [] for m in target_modules}
    zoho_token = ZohoToken.objects.filter(user=user).first()
    if zoho_token:
        access_token = zoho_token.access_token
        if not check_access_token_validity(access_token):
            access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, zoho_token.refresh_token)
            ZohoToken.objects.filter(user=user).update(access_token=access_token)
        
        for module in target_modules:
            try:
                m_data = get_module_fields(access_token, module)
                if "fields" in m_data:
                    fields = []
                    for f in m_data["fields"]:
                        fields.append({"api_name": f["api_name"], "label": f["field_label"]})
                    fields.sort(key=lambda x: x["label"])
                    module_fields[module] = fields
            except: pass
    return module_fields, target_modules

@login_required
def edit_credentials(request, credential_id):
    try:
        credential = CalendlyCredentials.objects.get(unique_id=credential_id, email=request.user.email)
    except CalendlyCredentials.DoesNotExist:
        return JsonResponse({'error': 'Credential not found.'}, status=404)

    module_fields, target_modules = _get_crm_fields_for_user(request.user)

    # Fetch templates
    templates = BookingEmailTemplate.objects.filter(credential=credential)

    if request.method == 'POST':
        try:
            # Get form data
            image_url = request.POST.get('image_url', '').strip() or credential.image_id
            company_name = request.POST.get('company_name')
            email_template = request.POST.get('email_template')
            
            # Handle Pre-fill Mappings (Dynamic Logic)
            PreFillMapping.objects.filter(user=request.user, calendly_account=credential).delete()
            q_keys = request.POST.getlist('q_key[]')
            z_fields = request.POST.getlist('z_field[]')
            z_modules = request.POST.getlist('z_module[]')
            for k, f, m in zip(q_keys, z_fields, z_modules):
                if k and f:
                    PreFillMapping.objects.create(
                        user=request.user, 
                        calendly_account=credential, 
                        question_key=k, 
                        zoho_field_api_name=f,
                        zoho_module=m or 'Leads'
                    )

            # Handle Multiple Email Templates
            BookingEmailTemplate.objects.filter(credential=credential).delete()
            t_names = request.POST.getlist('t_name[]')
            t_subjects = request.POST.getlist('t_subject[]')
            t_bodies = request.POST.getlist('t_body[]')
            t_modules = request.POST.getlist('t_module[]')
            for n, s, b, m in zip(t_names, t_subjects, t_bodies, t_modules):
                if n and b:
                    BookingEmailTemplate.objects.create(
                        user=request.user,
                        credential=credential,
                        template_name=n,
                        subject=s or "Invitation to Schedule a Meeting",
                        body=b,
                        zoho_module=m or 'Leads'
                    )

            # Update credentials in the database
            CalendlyCredentials.objects.filter(
                unique_id=credential_id, 
                email=request.user.email
            ).update(
                company_name=company_name,
                image_id=image_url,
                email_template=email_template
            )

            messages.success(request, f"Orchestration for '{company_name or credential.email}' updated successfully!")
            return redirect('list_credentials')

        except Exception as e:
            messages.error(request, f"Error updating hub logic: {str(e)}")
            return render(request, 'acuityscheduling/edit_credentials.html', {
                'credential': credential,
                'module_fields': module_fields,
                'module_fields_json': json.dumps(module_fields),
                'prefill_mappings': PreFillMapping.objects.filter(user=request.user, calendly_account=credential),
                'templates': templates,
                'error': str(e)
            })

    return render(request, 'acuityscheduling/edit_credentials.html', {
        'credential': credential,
        'module_fields': module_fields,
        'module_fields_json': json.dumps(module_fields),
        'prefill_mappings': PreFillMapping.objects.filter(user=request.user, calendly_account=credential),
        'templates': templates
    })


@login_required
def create_credentials(request):
    module_fields, target_modules = _get_crm_fields_for_user(request.user)
    
    if request.method == 'POST':
        image_url = request.POST.get('image_url', '').strip() or None
        company_name = request.POST.get('company_name', '').strip()
        email_template = request.POST.get('email_template', '').strip()
        email = request.POST.get('email', '').strip() or request.user.email

        field_errors = {}
        
        # Validate lengths based on model max_lengths
        if image_url and len(image_url) > 500:
            field_errors['image_url'] = f"Image URL is too long (Max 500 characters, currently {len(image_url)})."
        if company_name and len(company_name) > 100:
            field_errors['company_name'] = f"Hub Name is too long (Max 100 characters, currently {len(company_name)})."
        if email_template and len(email_template) > 700:
            field_errors['email_template'] = f"Email Template is too long (Max 700 characters, currently {len(email_template)})."
        if email and len(email) > 254:
            field_errors['email'] = f"Email address is too long (Max 254 characters, currently {len(email)})."

        if field_errors:
            messages.error(request, "Please correct the errors in the highlighted fields below.")
            return render(request, 'acuityscheduling/create_credentials.html', {
                'field_errors': field_errors,
                'form_data': request.POST,
                'module_fields': module_fields,
                'module_fields_json': json.dumps(module_fields),
            })

        try:
            #########################################################################################
            # Save credentials to the database - tokens are set later via OAuth callback
            #########################################################################################
            get_id, created = CalendlyCredentials.objects.update_or_create(
                email=email,
                defaults={
                    'image_id': image_url,
                    'company_name': company_name,
                    'email_template': email_template,
                }
            )

            messages.success(request, "Credentials created successfully!")
            return redirect('list_credentials')

        except Exception as e:
            print(f"Error creating credentials: {str(e)}")
            messages.error(request, f"Error creating credentials: {str(e)}")
            return render(request, 'acuityscheduling/create_credentials.html', {
                'error': str(e),
                'form_data': request.POST,
                'module_fields': module_fields,
                'module_fields_json': json.dumps(module_fields),
            })

    return render(request, 'acuityscheduling/create_credentials.html', {
        'module_fields': module_fields,
        'module_fields_json': json.dumps(module_fields),
    })


@login_required
def delete_credentials(request, credential_id):
    # Performance & Reliability: Direct QuerySet deletion avoids instance-level primary key checks
    # and ensures consistent cleanup even in complex relationship scenarios.
    deleted_count, _ = CalendlyCredentials.objects.filter(unique_id=credential_id, email=request.user.email).delete()
    if deleted_count > 0:
        messages.success(request, "Hub Orchestrator Protocol safely disconnected.")
    else:
        messages.warning(request, "Target protocol node not found or unauthorized access attempt.")
    return redirect('list_credentials')

def setup_webhook_view(request, credential_id):
    """View to handle webhook setup."""
    try:
        # Dynamically determine the base URL from the current request to ensure 
        # that webhooks are registered with the correct public-facing address.
        base_webhook_url = request.build_absolute_uri('/')[:-1]

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

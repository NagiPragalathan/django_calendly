from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import requests
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings

from base.models import CalendlyCredentials
from base.routes.tool_kit.mongo_tool import store_image_in_mongodb
from base.routes.tool_kit.calendly_tool import create_webhooks, get_webhooks_with_ids, delete_webhooks, CalendlyWebhookManager
from base.routes.tool_kit.zoho_tool import ensure_field_exists
from Finalty.settings import CALENDLY_CUSTOM_FIELDS
from base.routes.tool_kit.calendly_tool import setup_calendly_webhooks, cleanup_webhooks


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
def edit_credentials(request, credential_id):
    try:
        credential = CalendlyCredentials.objects.get(unique_id=credential_id, email=request.user.email)
    except CalendlyCredentials.DoesNotExist:
        return JsonResponse({'error': 'Credential not found.'}, status=404)

    if request.method == 'POST':
        try:
            # Get form data
            image = request.FILES.get('image')
            company_name = request.POST.get('company_name')
            email_template = request.POST.get('email_template')
            access_token = request.POST.get('access_token')  # Get from OAuth flow
            refresh_token = request.POST.get('refresh_token')  # Get from OAuth flow

            #########################################################################################
            # Save image to MongoDB if provided
            #########################################################################################
            if image:
                image_id = store_image_in_mongodb(image, request.user.email)
            else:
                image_id = credential.image_id

            #########################################################################################
            # Update credentials in the database
            #########################################################################################
            CalendlyCredentials.objects.filter(
                unique_id=credential_id, 
                email=request.user.email
            ).update(
                company_name=company_name,
                email_template=email_template,
                image_id=image_id,
                access_token=access_token or credential.access_token,
                refresh_token=refresh_token or credential.refresh_token
            )

            messages.success(request, "Credentials updated successfully!")
            return redirect('list_credentials')

        except Exception as e:
            print(f"Error updating credentials: {str(e)}")
            messages.error(request, f"Error updating credentials: {str(e)}")
            return render(request, 'acuityscheduling/edit_credentials.html', {
                'credential': credential,
                'error': str(e)
            })

    return render(request, 'acuityscheduling/edit_credentials.html', {
        'credential': credential
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

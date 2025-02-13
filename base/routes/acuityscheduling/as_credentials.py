from django.http import JsonResponse
from django.shortcuts import render
import requests
from django.shortcuts import get_object_or_404, redirect


from base.models import CalendlyCredentials
from base.routes.tool_kit.mongo_tool import store_image_in_mongodb

from base.routes.tool_kit.acuityscheduling_tool import create_webhooks, get_webhooks_with_ids, delete_webhooks
from base.routes.tool_kit.zoho_tool import ensure_field_exists
from Finalty.settings import ACUITY_CUSTOM_FIELDS


base_webhook_events = "https://django-acuity-scheduling.vercel.app/"

def list_credentials(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

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

def edit_credentials(request, credential_id):
    try:
        credential = CalendlyCredentials.objects.get(unique_id=credential_id, email=request.user.email)
    except CalendlyCredentials.DoesNotExist:
        return JsonResponse({'error': 'Credential not found.'}, status=404)

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        api_key = request.POST.get('api_key')
        image = request.FILES.get('image')
        company_name = request.POST.get('company_name')
        email_template = request.POST.get('email_template')

        if not user_id or not api_key:
            return JsonResponse({'error': 'User ID and API Key are required.'}, status=400)

        url = "https://acuityscheduling.com/api/v1/me"
        response = requests.get(url, auth=(user_id, api_key))

        if response.status_code != 200:
            return JsonResponse({'error': 'Invalid Calendly Credentials.'}, status=401)
        
        
        
        #########################################################################################
        # Save image to MongoDB if provided
        #########################################################################################
        if image:
            image_id = store_image_in_mongodb(image, request.user.email)
        else:
            image_id = credential.image_id
        
        #########################################################################################
        # Save credentials to the database
        #########################################################################################
        credential = CalendlyCredentials.objects.filter(unique_id=credential_id, email=request.user.email).update(
            user_id=user_id,
            api_key=api_key,
            company_name=company_name,
            email_template=email_template,
            base_url=response.json().get('schedulingPage'),
            embedCode=response.json().get('embedCode'),
            image_id=image_id
        )
        
        #########################################################################################
        # create webhooks
        #########################################################################################
        credential = CalendlyCredentials.objects.get(unique_id=credential_id, email=request.user.email)
        events = [    
            {"event": "appointment.rescheduled", "target": base_webhook_events+"acuity-webhook/create-meeting/"+ str(credential.unique_id)+'/'+ str(request.user.id) + '/'},
            {"event": "appointment.scheduled", "target": base_webhook_events+"acuity-webhook/create-meeting/"+str(credential.unique_id)+'/'+ str(request.user.id) + '/'},
            {"event": "appointment.canceled", "target": base_webhook_events+"acuity-webhook/create-meeting/"+str(credential.unique_id)+'/'+ str(request.user.id) + '/'},
        ]
        created = create_webhooks(events, user_id, api_key)
        print(created, "created")

        return JsonResponse({'message': 'Credential updated successfully!'}, status=200)

    return render(request, 'acuityscheduling/edit_credentials.html', {'credential': credential})


def create_credentials(request):
    if request.method == 'POST':
        image = request.FILES.get('image')
        company_name = request.POST.get('company_name')
        email_template = request.POST.get('email_template')
        
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
            email_template=email_template
        )
        
        #########################################################################################
        # create webhooks
        #########################################################################################
        events = [    
            {"event": "appointment.rescheduled", "target": base_webhook_events+"acuity-webhook/create-meeting/"+ str(get_id.unique_id)+'/'+ str(request.user.id) + '/'},
            {"event": "appointment.scheduled", "target": base_webhook_events+"acuity-webhook/create-meeting/"+str(get_id.unique_id)+'/'+ str(request.user.id) + '/'},
            {"event": "appointment.canceled", "target": base_webhook_events+"acuity-webhook/create-meeting/"+str(get_id.unique_id)+'/'+ str(request.user.id) + '/'},
        ]
        # created = create_webhooks(events, user_id, api_key)
        # print(created, "created")
        
        #########################################################################################
        # create custom fields
        #########################################################################################
        # for i in ACUITY_CUSTOM_FIELDS:
        #     print(i, "is now being creating...")
        #     created = ensure_field_exists(request.user, i)
        #     print(created, "created")

        return JsonResponse({'message': 'Credential created successfully!'}, status=201)

    return render(request, 'acuityscheduling/create_credentials.html')


def delete_credentials(request, credential_id):
    credential = CalendlyCredentials.objects.get(unique_id=credential_id, email=request.user.email)
    # targets = get_webhooks_with_ids(credential.user_id, credential.api_key)
    # print(targets, "targets")
    # for target in targets:
    #     print(target, "target")
        # if str(credential.unique_id) in target[1]:
        #     delete_webhooks(target[0], credential.user_id, credential.api_key)
    CalendlyCredentials.objects.filter(unique_id=credential_id, email=request.user.email).delete()
    return redirect('list_credentials')

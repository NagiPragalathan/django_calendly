from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from Finalty.settings import ACUITY_WEBHOOK_EVENTS, ACUITY_CUSTOM_FIELDS
from base.models import CalendlyCredentials
import requests, json
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta, timezone
from django.core.paginator import Paginator
from django.utils.html import escape
from django.db.models import Q
from datetime import datetime
from django.utils.dateparse import parse_datetime
from requests.auth import HTTPBasicAuth
from base.routes.tool_kit.acuityscheduling_tool import create_webhooks
from base.routes.tool_kit.secract_del import delete_all_webhooks
from base.routes.tool_kit.mongo_tool import store_image_in_mongodb, get_image_from_mongodb
from base.routes.tool_kit.zoho_tool import ensure_field_exists
    
# def store_credentials(request):
#     if request.method == 'POST':
#         user_id = request.POST.get('user_id')
#         api_key = request.POST.get('api_key')
#         image = request.FILES.get('image')
#         company_name = request.POST.get('company_name')
#         email_template = request.POST.get('email_template')

#         # Validate inputs
#         if not user_id or not api_key:
#             return JsonResponse({'error': 'Both User ID and API Key are required.'}, status=400)

#         url = "https://acuityscheduling.com/api/v1/me"
#         response = requests.get(url, auth=(user_id, api_key))

#         if response.status_code != 200:
#             return JsonResponse({'error': 'Invalid Acuity credentials.'}, status=401)

#         #########################################################################################
#         # Save image to MongoDB if provided
#         #########################################################################################
#         image_id = None
#         if image:
#             image_id = store_image_in_mongodb(image, request.user.email)
#             print(image_id, "image_id stored")
            
            
#         #########################################################################################
#         # Save credentials to the database
#         #########################################################################################
#         try:
#             obj = CalendlyCredentials.objects.get(email=request.user.email)
#             print(obj, obj.user_id, obj.image_id, obj.base_url, obj.embedCode, obj.api_key)
#             if image == None:
#                 image_id = obj.image_id
#             if company_name == None:
#                 company_name = obj.company_name
#             if email_template == None:
#                 email_template = obj.email_template
                
#             CalendlyCredentials.objects.filter(email=request.user.email).update(
#                 user_id=user_id,
#                 image_id=image_id,
#                 base_url=response.json().get('schedulingPage'),
#                 embedCode=response.json().get('embedCode'),
#                 api_key=api_key,
#                 company_name=company_name,
#                 email_template=email_template
#             )
#         except CalendlyCredentials.DoesNotExist:
#             created = CalendlyCredentials.objects.create(
#                 email=request.user.email,
#                 user_id=user_id,
#                 image_id=image_id,
#                 base_url=response.json().get('schedulingPage'),
#                 embedCode=response.json().get('embedCode'),
#                 api_key=api_key,
#                 company_name=company_name,
#                 email_template=email_template
#             )
#             print("created:", created)
#         #########################################################################################
#         # create webhooks
#         #########################################################################################
#         created = create_webhooks(ACUITY_WEBHOOK_EVENTS, user_id, api_key)
#         print(created, "created")
        
#         #########################################################################################
#         # create custom fields
#         #########################################################################################
#         for i in ACUITY_CUSTOM_FIELDS:
#             print(i, "is now being creating...")
#             created = ensure_field_exists(request.user, i)
#             print(created, "created")

#         return JsonResponse({'message': 'Credentials and image saved successfully!'}, status=201)
    
#     try:
#         obj = CalendlyCredentials.objects.get(email=request.user.email)
#         out_data = {
#             'user_id': obj.user_id,
#             'api_key': obj.api_key,
#             'image_id': obj.image_id,
#             'base_url': obj.base_url,
#             'embedCode': obj.embedCode,
#             'company_name': obj.company_name,
#             'email_template': obj.email_template
#         }
#     except CalendlyCredentials.DoesNotExist:
#         out_data = {
#             'user_id': '',
#             'api_key': '',
#             'image_id': '',
#             'base_url': '',
#             'embedCode': '',
#             'company_name': '',
#             'email_template': ''
#         }

#     return render(request, 'acuityscheduling/store_credentials.html', out_data)


@login_required
def list_appointments(request):
    email = request.user.email

    try:
        credentials = CalendlyCredentials.objects.get(email=email)
    except CalendlyCredentials.DoesNotExist:
        return render(request, 'acuityscheduling/appointments.html', {
            'error': 'No Acuity credentials found for your account. '
                     '<a href="/store-credentials/" class="text-blue-600 underline">Store credentials</a>'
        })

    user_id = credentials.user_id
    api_key = credentials.api_key

    base_url = 'https://acuityscheduling.com/api/v1'
    appointments_endpoint = f'{base_url}/appointments'

    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=30)

    start_date_str = now.isoformat()
    end_date_str = end_date.isoformat()

    auth = (user_id, api_key)
    params = {
        'minDate': start_date_str,
        'maxDate': end_date_str,
        'direction': 'ASC' 
    }

    try:
        response = requests.get(appointments_endpoint, auth=auth, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        appointments = response.json()
    except requests.exceptions.RequestException as e:
        # Handle API errors gracefully
        return render(request, 'acuityscheduling/appointments.html', {
            'error': f"Failed to fetch appointments. Please try again later.<br>Error: {str(e)}"
        })

    # Render the appointments page with the fetched appointments
    return render(request, 'acuityscheduling/appointments.html', {
        'appointments': appointments,
        'start_date': start_date_str,
        'end_date': end_date_str
    })
    


@login_required
def past_appointments(request):
    try:
        credentials = CalendlyCredentials.objects.get(email=request.user.email)
        user_id = credentials.user_id
        api_key = credentials.api_key
    except CalendlyCredentials.DoesNotExist:
        return render(request, 'acuityscheduling/past_appointments.html', {
            'error': 'No credentials found. Please store your credentials first.'
        })

    # API call
    base_url = 'https://acuityscheduling.com/api/v1'
    appointments_endpoint = f'{base_url}/appointments'
    now = datetime.now()
    auth = (user_id, api_key)
    params = {'maxDate': now.isoformat(), 'direction': 'DESC'}

    try:
        response = requests.get(appointments_endpoint, auth=auth, params=params)
        response.raise_for_status()
        appointments = response.json()
    except requests.RequestException as e:
        return render(request, 'acuityscheduling/past_appointments.html', {
            'error': f"Failed to fetch appointments. Error: {str(e)}"
        })

    service_types = sorted({appt['type'] for appt in appointments if appt['type']})

    query = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    start_time = request.GET.get('start_time')  # Format: HH:MM
    end_time = request.GET.get('end_time')  # Format: HH:MM
    service_type = request.GET.get('service_type')  # Selected service type
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if query:
        appointments = [
            appt for appt in appointments
            if query.lower() in str(appt.values()).lower()
        ]

    if start_date:
        appointments = [
            appt for appt in appointments
            if parse_datetime(appt['datetime']).date() >= datetime.strptime(start_date, '%Y-%m-%d').date()
        ]
    if end_date:
        appointments = [
            appt for appt in appointments
            if parse_datetime(appt['datetime']).date() <= datetime.strptime(end_date, '%Y-%m-%d').date()
        ]

    if start_time:
        start_time_dt = datetime.strptime(start_time, '%H:%M').time()
        appointments = [
            appt for appt in appointments
            if parse_datetime(appt['datetime']).time() >= start_time_dt
        ]
    if end_time:
        end_time_dt = datetime.strptime(end_time, '%H:%M').time()
        appointments = [
            appt for appt in appointments
            if parse_datetime(appt['datetime']).time() <= end_time_dt
        ]

    if service_type:
        appointments = [appt for appt in appointments if appt['type'] == service_type]

    if min_price:
        appointments = [appt for appt in appointments if float(appt['price']) >= float(min_price)]
    if max_price:
        appointments = [appt for appt in appointments if float(appt['price']) <= float(max_price)]
        
    print(appointments)

    paginator = Paginator(appointments, 21)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'acuityscheduling/past_appointments.html', {
        'page_obj': page_obj,
        'request': request,
        'service_types': service_types
    })


def appointment_types_view(request):
    """
    Fetch and display appointment types with links.
    """
    email = request.user.email

    try:
        credentials = CalendlyCredentials.objects.get(email=email)
    except CalendlyCredentials.DoesNotExist:
        return render(request, 'acuityscheduling/appointments.html', {
            'error': 'No Acuity credentials found for your account. '
                     '<a href="/store-credentials/" class="text-blue-600 underline">Store credentials</a>'
        })

    user_id = credentials.user_id
    api_key = credentials.api_key
    base_url = "https://acuityscheduling.com/api/v1"
    appointment_types_endpoint = f"{base_url}/appointment-types"
    auth = HTTPBasicAuth(user_id, api_key)

    try:
        response = requests.get(appointment_types_endpoint, auth=auth)
        response.raise_for_status()
        appointment_types = response.json()

        # Add links and color tags
        for appt_type in appointment_types:
            appt_type["link"] = f"https://app.acuityscheduling.com/schedule.php?owner={user_id}&appointmentType={appt_type.get('id')}"

        # Get unique colors for filter
        unique_colors = list(set(appt_type["color"] for appt_type in appointment_types if appt_type["color"]))

        # Filter by color if specified
        selected_color = request.GET.get("color")
        if selected_color:
            appointment_types = [appt for appt in appointment_types if appt["color"] == selected_color]

        return render(request, 'acuityscheduling/appointment_types.html', {
            'appointment_types': appointment_types,
            'colors': unique_colors,
        })

    except requests.RequestException as e:
        return render(request, 'acuityscheduling/appointment_types.html', {'error': f"Failed to fetch appointment types: {str(e)}"})


def acuity_dashboard(request):
    """
    Fetch and display data for Acuity Scheduling Dashboard.
    """
    email = request.user.email

    try:
        credentials = CalendlyCredentials.objects.get(email=email)
    except CalendlyCredentials.DoesNotExist:
        return render(request, 'acuityscheduling/dashboard.html', {
            'error': 'No Acuity credentials found for your account. Store credentials by clicking &nbsp;&nbsp;'
                     '<a href="/store-credentials/" class="text-blue-600 underline">here</a>'
        })

    USER_ID = credentials.user_id
    API_KEY = credentials.api_key
    base_url = "https://acuityscheduling.com/api/v1"
    auth = HTTPBasicAuth(USER_ID, API_KEY)

    # Endpoints
    appointment_types_endpoint = f"{base_url}/appointment-types"
    past_appointments_endpoint = f"{base_url}/appointments"

    service_types = []
    past_appointments = []
    total_revenue = 0

    try:
        # Fetch service types
        response = requests.get(appointment_types_endpoint, auth=auth)
        response.raise_for_status()
        service_types = response.json()

        # Fetch past appointments
        params = {'maxDate': '2024-11-26', 'direction': 'DESC'}
        response = requests.get(past_appointments_endpoint, auth=auth, params=params)
        response.raise_for_status()
        past_appointments = response.json()

        # Calculate total revenue from service types
        total_revenue = sum(float(service.get("price", 0)) for service in service_types)

        # Process data for visualizations
        service_price_data = [
            {"name": service["name"], "price": float(service.get("price", 0))} for service in service_types
        ]
        appointment_status_data = {
            "completed": sum(1 for appt in past_appointments if appt.get("status") == "completed"),
            "upcoming": sum(1 for appt in past_appointments if appt.get("status") == "upcoming"),
            "cancelled": sum(1 for appt in past_appointments if appt.get("status") == "cancelled"),
        }

        # Process appointment history data
        sorted_dates = sorted(set(appt['date'] for appt in past_appointments))
        appointment_history = [sum(1 for appt in past_appointments if appt['date'] == date) for date in sorted_dates]

        # Process clients data
        clients = [{"firstName": appt.get("firstName"), "lastName": appt.get("lastName"), "email": appt.get("email")} for appt in past_appointments]

        # Pass all processed data to the template
        context = {
            "service_types": service_types,
            "past_appointments": past_appointments,
            "total_revenue": total_revenue,
            "service_price_data": service_price_data,
            "appointment_status_data": appointment_status_data,
            "appointment_history": appointment_history,
            "sorted_dates": sorted_dates,
            "clients": clients,
        }

        return render(request, 'acuityscheduling/dashboard.html', context)

    except requests.RequestException as e:
        return render(request, 'acuityscheduling/dashboard.html', {'error': f"Failed to fetch data: {str(e)}"})


def reset_webhook_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        api_key = request.POST.get('api_key')
        if user_id and api_key:
            try:
                print(f"User ID: {user_id}, API Key: {api_key}")
                delete_all_webhooks(user_id, api_key)
                # Simulate webhook reset logic
                return JsonResponse({'success': True, 'message': 'Webhook reset successful.'})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        else:
            return JsonResponse({'error': 'Missing user_id or api_key'}, status=400)
    return render(request, 'acuityscheduling/reset_webhook.html')

def acuity_schedule(request):
    email = request.user.email
    print(request.image_url)
    try:
        credentials = CalendlyCredentials.objects.get(email=email)
    except CalendlyCredentials.DoesNotExist:
        return render(request, 'acuityscheduling/acuity_schedule.html', {
            'error': 'No Acuity credentials found for your account. Store credentials by clicking &nbsp;&nbsp;'
                     '<a href="/store-credentials/" class="text-blue-600 underline">here</a>'
        })
    return render(request, 'acuityscheduling/acuity_schedule.html', {'embedCode': credentials.embedCode})


def serve_image(request, image_id):
    """
    Serve the image stored in MongoDB by its ID.
    :param image_id: The ID of the image in MongoDB.
    :return: An HTTP response containing the image content.
    """
    try:
        # Retrieve the image content
        image_content = get_image_from_mongodb(image_id)

        # Serve the image as a response
        return HttpResponse(image_content, content_type="image/jpeg")
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.models import User
from base.models import Profile
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.db import transaction, IntegrityError
from google.oauth2.id_token import verify_oauth2_token

from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
import os

# Allow non-HTTPS requests during development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def g_login(request):
    # if request.user.is_authenticated:
    #     return redirect('/dashboard/')
    # else:
        return render(request, 'auth/g_login.html')

def google_login(request):
    """
    Initiates the Google OAuth login process.
    Redirects to Google's authentication page.
    """
    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    auth_url, state = flow.authorization_url(
        prompt='consent',
        include_granted_scopes='true',
    )
    request.session['state'] = state  # Save the state to validate later
    return redirect(auth_url)

def google_callback(request):
    state = request.session.get('state', None)
    
    # If state is missing, return an error
    if not state:
        return JsonResponse({"error": "Invalid state"}, status=400)

    # Initialize OAuth flow
    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    # Verify the token and allow a small clock skew
    credentials = flow.credentials
    try:
        id_info = verify_oauth2_token(
            credentials.id_token,
            requests.Request(),
            clock_skew_in_seconds=10  # Allowing 10 seconds of clock skew
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    # Extract user details from the ID token
    email = id_info.get("email")
    first_name = id_info.get("given_name")
    last_name = id_info.get("family_name")
    picture = id_info.get("picture")

    try:
        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # Get or create the user
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                },
            )

            Profile.objects.filter(user=user).update(profile_image_url=picture)

    except IntegrityError as e:
        return JsonResponse({"error": "A database error occurred: " + str(e)}, status=500)

    # Log the user in
    login(request, user)
    return redirect(settings.LOGIN_REDIRECT_URL)

def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'auth/signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'auth/signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, 'auth/signup.html')

        # Create the user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, "Account created successfully!")
        return redirect('login')

    return render(request, 'auth/signup.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect('/')  # Redirect to home or any other page
        else:
            messages.error(request, "Invalid username or password!")
        return render(request, 'auth/login.html')

    return render(request, 'auth/login.html')

from .models import CalendlyCredentials

class UserDataMiddleware:
    """
    Middleware to add user-related data (e.g., image URL and company name) to the request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add user-specific data only if the user is authenticated
        if request.user.is_authenticated:
            try:
                # Retrieve Calendly Credentials for the logged-in user
                credentials = CalendlyCredentials.objects.filter(email=request.user.email).first()
                if credentials:
                    # Attach the image URL to the request
                    if credentials.image_id:
                        request.image_url = f"http://{request.get_host()}/image/{credentials.image_id}/"
                    else:
                        request.image_url = "https://avatars.githubusercontent.com/u/150781803?s=200&v=4"

                    # Attach the company name to the request
                    request.company_name = credentials.company_name
                else:
                    request.image_url = "https://avatars.githubusercontent.com/u/150781803?s=200&v=4"
                    request.company_name = 'susanoox'
            except Exception:
                request.image_url = "https://avatars.githubusercontent.com/u/150781803?s=200&v=4"
                request.company_name = 'susanoox'
        else:
            request.image_url = "https://avatars.githubusercontent.com/u/150781803?s=200&v=4"
            request.company_name = 'susanoox'

        response = self.get_response(request)
        return response

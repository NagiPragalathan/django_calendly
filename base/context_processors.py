from base.models import CalendlyCredentials
from base.utils import get_active_hub

def calendly_context(request):
    if not request.user.is_authenticated:
        return {}
        
    active_credential = get_active_hub(request)
    credentials = CalendlyCredentials.objects.filter(email=request.user.email)
    
    return {
        'all_hubs': credentials,
        'active_hub': active_credential
    }

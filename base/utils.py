from base.models import CalendlyCredentials

def get_active_hub(request):
    """Retrieve the active hub for the user based on session or primary flag."""
    if not request.user.is_authenticated:
        return None
        
    active_id = request.session.get('active_calendly_id')
    user_email = request.user.email
    credentials = None
    
    try:
        if active_id:
            credentials = CalendlyCredentials.objects.filter(unique_id=active_id, email=user_email).first()
            
        if not credentials:
            # Fallback to primary
            credentials = CalendlyCredentials.objects.filter(email=user_email, is_primary=True).first()
            
        if not credentials:
            # Fallback to first available
            credentials = CalendlyCredentials.objects.filter(email=user_email).first()
    except Exception as e:
        print(f"Database error in get_active_hub: {e}")
        # Final fallback: Fetch all for user and find primary in memory if DB query failed
        all_creds = list(CalendlyCredentials.objects.filter(email=user_email))
        if all_creds:
            primary = next((c for c in all_creds if getattr(c, 'is_primary', False)), None)
            credentials = primary or all_creds[0]
        
    return credentials

from base.models import CalendlyCredentials

def get_active_hub(request):
    """Retrieve the active hub for the user based on session or primary flag."""
    if not request.user.is_authenticated:
        return None
        
    active_id = request.session.get('active_calendly_id')
    user_email = request.user.email
    credentials = None
    
    try:
        # Fetch all credentials for the user once to avoid multiple failing SQL queries
        all_creds = list(CalendlyCredentials.objects.filter(email=user_email))
        
        if not all_creds:
            return None

        # 1. Search by session ID (using string comparison for safety)
        if active_id:
            active_str = str(active_id)
            credentials = next((c for c in all_creds if str(c.unique_id) == active_str), None)
            if credentials: return credentials

        # 2. Fallback to Primary
        credentials = next((c for c in all_creds if getattr(c, 'is_primary', False)), None)
        if credentials: return credentials

        # 3. Last fallback: First one
        return all_creds[0]

    except Exception as e:
        import traceback
        print(f"CRITICAL: get_active_hub failed with exception: {repr(e)}")
        # If even basic filter fails, return ANY credential to prevent total crash
        try:
            return CalendlyCredentials.objects.first()
        except:
            return None

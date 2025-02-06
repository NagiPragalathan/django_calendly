from django.shortcuts import render, redirect, get_object_or_404
from base.models import Settings
from django.contrib.auth.decorators import login_required


@login_required
def settings_form(request):
    """Handles both creating and updating user settings."""
    user = request.user  # Get logged-in user

    # Check if user already has settings
    settings_instance = Settings.objects.filter(user=user).first()

    if request.method == "POST":
        leads_to_store = request.POST.get("leads_to_store")
        lead_source = request.POST.get("lead_source")

        if settings_instance:
            Settings.objects.filter(user=user).update(
                leads_to_store=leads_to_store,
                lead_source=lead_source
            )
        else:
            Settings.objects.create(
                user=user,
                leads_to_store=leads_to_store,
                lead_source=lead_source
            )

        return redirect("settings_form")  # Redirect back to the form page

    return render(request, "settings_form.html", {"settings": settings_instance})

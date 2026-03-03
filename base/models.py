from django.db import models
from django.contrib.auth.models import User
import uuid
from datetime import datetime, timedelta

class CalendlyCredentials(models.Model):
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True)
    access_token = models.CharField(max_length=400)
    refresh_token = models.CharField(max_length=400)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    base_url = models.URLField(blank=True, null=True)
    embedCode = models.CharField(max_length=400, blank=True, null=True)
    email_template = models.CharField(max_length=700, blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    image_id = models.CharField(max_length=50, blank=True, null=True)  # Updated field
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} ({'Primary' if self.is_primary else 'Regular'})"

    def is_token_expired(self):
        """Check if the access token has expired."""
        if not self.token_expires_at:
            return True
        return datetime.now(self.token_expires_at.tzinfo) >= self.token_expires_at

    def update_token_expiration(self, expires_in):
        """Update token expiration time."""
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        self.save()

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_image_url = models.URLField(blank=True, null=True)  # Store image URL

    def __str__(self):
        return self.user.username


# class CalendlyCredentials(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='acuity_credentials')
#     access_token = models.CharField(max_length=255, unique=True)
#     refresh_token = models.CharField(max_length=255, unique=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.user.username

class ZohoToken(models.Model):
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    org_data = models.CharField(max_length=255)
    access_token = models.TextField()
    refresh_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Zoho Token for {self.user.username} - {self.org_data}"

class Settings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leads_to_store = models.CharField(max_length=20, choices=[('Leads', 'Leads'), ('Contacts', 'Contacts')], default='Contacts')
    lead_source = models.CharField(max_length=255, default='Acuity Scheduling')
    use_default_mapping = models.BooleanField(default=True)
    field_mappings = models.JSONField(default=dict, blank=True)
    webhook_base_url = models.URLField(max_length=500, null=True, blank=True, help_text="Public URL for webhooks (e.g., ngrok)")

    def __str__(self):
        return self.user.username

class SmtpSettings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    smtp_server = models.CharField(max_length=255, default='smtp.gmail.com')
    smtp_port = models.IntegerField(default=587)
    smtp_user = models.EmailField()
    smtp_password = models.CharField(max_length=255)  
    use_tls = models.BooleanField(default=True)

    def __str__(self):
        return f"SMTP: {self.smtp_user}"

class PreFillMapping(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    calendly_account = models.ForeignKey(CalendlyCredentials, on_delete=models.CASCADE)
    # Question mapping: a1, a2, etc. to Zoho Field API name
    question_key = models.CharField(max_length=50) # 'a1', 'a2', etc.
    zoho_field_api_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.question_key} -> {self.zoho_field_api_name}"

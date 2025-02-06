from django.db import models
from django.contrib.auth.models import User
import uuid
class CalendlyCredentials(models.Model):
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True)
    user_id = models.CharField(max_length=20)
    api_key = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    base_url = models.URLField(blank=True, null=True)
    embedCode = models.CharField(max_length=400, blank=True, null=True)
    email_template = models.CharField(max_length=700, blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    image_id = models.CharField(max_length=50, blank=True, null=True)  # Updated field

    def __str__(self):
        return self.email

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
        return f"{self.account_name} ({self.email}) - {self.status}"

class Settings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leads_to_store = models.CharField(max_length=20, choices=[('Leads', 'Leads'), ('Contacts', 'Contacts')], default='Contacts')
    lead_source = models.CharField(max_length=255, default='Acuity Scheduling')

    def __str__(self):
        return self.user.username

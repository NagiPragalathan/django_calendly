"""Finalty URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from base.routes.acuityscheduling.as_credentials import *
from base.routes.zoho.zoho_auth import *
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from Finalty import settings
from django.contrib.sitemaps.views import sitemap
from base.sitemaps import StaticViewSitemap

from django.contrib.auth import views as auth_views
from base.routes.auth_management import *
from base.routes.acuityscheduling_views import *
from base.routes.acuityscheduling_del import *
from base.routes.acuityscheduling_api import *
from base.routes.acuityscheduling.acuityscheduling_settings import *
from base.routes.acuityscheduling.calendly_auth import *

sitemaps = {
    'static': StaticViewSitemap,
}

auth = [
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('g_login/', g_login, name='g_login'),
    path('google/login/', google_login, name='google-login'),
    path('google/callback/', google_callback, name='google-callback'),
]

urlpatterns = [
    path('', acuity_dashboard, name='dashboard'),
    path("admin/", admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

acuityscheduling_urls = [
    # path('store-credentials/', store_credentials, name='store_credentials'), i have created the new route for that [create_credentials]
    path('appointments/', list_appointments, name='list_appointments'),
    path('past-appointments/', past_appointments, name='past_appointments'),
    path('appointments-types/', appointment_types_view, name='appointment_types'),
    path('dashboard/', acuity_dashboard, name='acuity_dashboard'),
    path('acuity/connect/', connect_acuity_scheduling, name='connect_acuity_scheduling'),
    path('acuity/callback/', ac_callback, name='acuity_callback'),
    path('reset-webhook/', reset_webhook_view, name='reset_webhook'),
    path('acuity/schedule/', acuity_schedule, name='acuity_schedule'),
    path('image/<str:image_id>/', serve_image, name='serve_image'),
    
    path('credentials/', list_credentials, name='list_credentials'),
    path('credentials/create/', create_credentials, name='create_credentials'),
    path('credentials/<uuid:credential_id>/edit/', edit_credentials, name='edit_credentials'),
    path('credentials/<uuid:credential_id>/delete/', delete_credentials, name='delete_credentials'),  # New delete URL
    
    path("settings/", settings_form, name="settings_form"),
]

acuityscheduling_api_urls = [
    path('calendly-webhook/meeting/<uuid:credential_id>/<int:user_id>/', calendly_webhook_create_meeting, name='calendly_webhook_create_meeting'),
]

zoho_urls = [
    path('zoho-auth/', zoho_index, name='zoho_auth'),
    path('zoho-callback/', zoho_callback, name='zoho_callback'),
]

calendly_urls = [
    path('oauth/<uuid:credential_id>/', calendly_auth, name='calendly_auth'),
    path('oauth/callback/', calendly_callback, name='calendly_callback'),
]

urlpatterns += auth
urlpatterns += acuityscheduling_urls
urlpatterns += acuityscheduling_api_urls
urlpatterns += zoho_urls
urlpatterns += calendly_urls
urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


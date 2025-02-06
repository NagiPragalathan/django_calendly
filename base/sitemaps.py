from django.contrib import sitemaps
from django.urls import reverse

class StaticViewSitemap(sitemaps.Sitemap):
    changefreq = 'monthly'  # Possible values: always, hourly, daily, weekly, monthly, yearly, never
    priority = 0.5  # A number between 0.0 and 1.0 indicating the priority of the URL

    def items(self):
        return ['underdev', 'home', "list_out", "robots.txt", "contact_form"]  # View names or any other objects

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        return None
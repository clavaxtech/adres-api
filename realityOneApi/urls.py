"""realityOneApi URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
router = routers.DefaultRouter()

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', include(router.urls)),
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api-users/', include('api.users.urls')),
    path('api-settings/', include('api.settings.urls')),
    path('api-cms/', include('api.cms.urls')),
    path('api-home/', include('api.home.urls')),
    path('api-notifications/', include('api.notifications.urls')),
    path('api-property/', include('api.property.urls')),
    path('api-project/', include('api.project.urls')),
    path('api-network/', include('api.network.urls')),
    path('api-contact/', include('api.contact.urls')),
    path('api-faq/', include('api.faq.urls')),
    path('api-bid/', include('api.bid.urls')),
    path('api-blog/', include('api.blog.urls')),
    path('api-advertisement/', include('api.advertisement.urls')),
    path('api-payments/', include('api.payments.urls')),
]

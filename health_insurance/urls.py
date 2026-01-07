"""
URL configuration for health_insurance project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from users.views import UserLoginView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls', namespace='users')),
    path('policy/', include('policy.urls')),
    path('admin_panel/', include('admin_panel.urls')),
    path('claims/', include('claims.urls')),
    path('network_provider/', include('network_provider.urls')),
    path('feedback_support/', include('feedback_support.urls')),
    path('', UserLoginView.as_view(), name='home_login'),
   ]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

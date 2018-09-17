"""lantern URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

from rest_framework.documentation import include_docs_urls
from rest_framework_jwt.views import obtain_jwt_token, \
                                     refresh_jwt_token, \
                                     verify_jwt_token


import xadmin


urlpatterns = [
    path('admin/', admin.site.urls),
    path('xadmin/', xadmin.site.urls),

    path('docs/', include_docs_urls(title='Lantern API')),
    path('api-auth/', include('rest_framework.urls')),

    # jwt
    path('jwt/auth/', obtain_jwt_token),
    path('jwt/refresh/', refresh_jwt_token),
    path('jwt/verify/', verify_jwt_token),

    # account
    path('account/', include('account.urls', namespace='account')),
    path('action/', include('action.urls', namespace='action')),

    # tft
    path('tft/', include('tft.urls', namespace='tft')),
]

if settings.DEBUG:
    # It is not necessary to add the urlpattern of static,
    # runerver will do this automatically when DEBUG is set to True.
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

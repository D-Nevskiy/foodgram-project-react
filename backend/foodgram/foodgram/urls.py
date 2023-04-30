from api.views import CustomObtainAuthToken, LogoutView
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/token/login/', CustomObtainAuthToken.as_view(),
         name='custom_auth_token'),
    path('api/auth/token/logout/', LogoutView.as_view(), name='token_logout'),
    path('api/', include('api.urls', namespace='api'))
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserViewSet,
    dealer_register,
    forgot_password,
    login_view,
    logout_view,
    me_view,
    reset_password,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")

urlpatterns = [
    path("login/", login_view),
    path("dealer-register/", dealer_register),
    path("logout/", logout_view),
    path("me/", me_view),
    path("refresh/", TokenRefreshView.as_view()),
    path("forgot-password/", forgot_password),
    path("reset-password/", reset_password),
    path("", include(router.urls)),
]

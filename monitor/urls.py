from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

urlpatterns = [
    path("", views.site_list, name="site_list"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("sites/add/", views.site_create, name="site_create"),
    path("sites/<int:pk>/delete/", views.site_delete, name="site_delete"),
    path("sites/<int:pk>/check-now/", views.site_check_now, name="site_check_now"),
    path("sites/<int:pk>/history/", views.change_history, name="change_history"),
]

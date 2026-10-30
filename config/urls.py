from django.urls import path
from monitoring import views
 
urlpatterns = [
    path("", views.index),
    path("api/state/", views.state),
]

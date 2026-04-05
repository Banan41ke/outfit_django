from django.urls import path
from . import views

urlpatterns = [
    path('', views.MainView.as_view(), name='main'),
    path('category/<str:category_name>/', views.CategoryDetailView.as_view(), name='category'),
]
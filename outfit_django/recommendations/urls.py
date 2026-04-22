from django.urls import path
from . import views

urlpatterns = [
    path('', views.MainView.as_view(), name='main'),
    path('results/', views.ResultsView.as_view(), name='results'),  # <-- ЭТО ОБЯЗАТЕЛЬНО
    path('category/<str:category_name>/', views.CategoryDetailView.as_view(), name='category'),
]
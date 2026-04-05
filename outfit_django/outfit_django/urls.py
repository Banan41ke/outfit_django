from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from recommendations import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.MainView.as_view(), name='main'),
    path('results/', views.ResultsView.as_view(), name='results'),
]

# 👇 Раздача медиа и data ТОЛЬКО в debug
if settings.DEBUG:
    # media (загруженные пользователем фото)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # 🔥 твои спарсенные изображения
    urlpatterns += static('/data/', document_root=settings.BASE_DIR / 'data')
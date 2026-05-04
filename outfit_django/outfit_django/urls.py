from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('recommendations.urls')),
]

# MEDIA (пользовательские файлы)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # 👇 DATASET (твои вещи)
    urlpatterns += [
        path('dataset/<path:path>', serve, {
            'document_root': settings.DATASET_ROOT,
        }),
    ]
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def health_check(request):
    return HttpResponse("ok", status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("archiver/", include("archiver.urls")),
    path("health/", health_check),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

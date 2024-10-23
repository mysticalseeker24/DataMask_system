from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("llm_anon_app/", include("llm_anon_app.urls")),
    path("", include("llm_anon_app.urls")),
    path("admin/", admin.site.urls),
]
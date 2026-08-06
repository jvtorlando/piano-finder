from django.contrib import admin
from django.urls import path
from pianos import views
from django.conf import settings
from django.conf.urls.static import static

handler403 = 'pianos.views.permission_denied'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.lista_pianos, name='home'),
    path('adicionar/', views.adicionar_piano, name='adicionar_piano'),
    path('piano/<int:piano_id>/', views.detalhe_piano, name='detalhe_piano'),
    path('piano/<int:piano_id>/like/', views.like_piano, name='like_piano'),
    path('piano/<int:piano_id>/avaliar/', views.avaliar_piano, name='avaliar_piano'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

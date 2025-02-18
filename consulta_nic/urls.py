from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('consultar/', views.consultar_api, name='consultar_api'),
]



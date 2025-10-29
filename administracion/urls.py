from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RoleViewSet, PermissionViewSet, ClienteViewSet, CiudadViewSet, DepartamentoViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'clientes', ClienteViewSet)
router.register(r'ciudades', CiudadViewSet)
router.register(r'departamentos', DepartamentoViewSet)


urlpatterns = [
    path('', include(router.urls)),
]

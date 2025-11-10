from django.db.models import ProtectedError
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.contrib.auth.models import User, Group, Permission
from .serializers.serializers_usuario import UserSerializer
from .serializers.serializers_rol import RoleSerializer, PermissionSerializer
from .serializers.serializers_cliente import ClienteSerializer, CiudadSerializer, DepartamentoSerializer
from administracion.models import Departamento, Ciudad, Cliente, RegistroBitacora
from .serializers.serializers_bitacora import RegistroBitacoraSerializer
from .core.utils import registrar_bitacora
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt 
from rest_framework.views import APIView


from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken


# ==================== VISTAS DE AUTENTICACIÓN ====================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extiende el serializer por defecto para añadir datos del usuario
    tanto al token como a la respuesta JSON del login.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Añade campos personalizados dentro del payload del token
        token["username"] = user.username
        token["email"] = getattr(user, "email", "")
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Añade información del usuario a la respuesta del endpoint de login
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": getattr(self.user, "email", ""),
            "is_staff": self.user.is_staff,
        }
        return data


@method_decorator(csrf_exempt, name="dispatch")
class CustomTokenObtainPairView(TokenObtainPairView):
    """Vista de login que usa el serializer personalizado.

    - Permite peticiones desde el frontend (AllowAny).
    - No usa autenticación previa (authentication_classes vacías) para permitir login.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """Cierra sesión invalidando (blacklist) el refresh token.

    Body esperado: { "refresh": "<refresh_token>" }
    Requiere que la app 'rest_framework_simplejwt.token_blacklist' esté en INSTALLED_APPS
    y que se hayan corrido las migraciones.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout exitoso"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        rol_info = instance.groups.first()
        rol_nombre = rol_info.name if rol_info else 'Sin rol'
        descripcion = f"Usuario '{instance.username}' creado con email '{instance.email}' y rol '{rol_nombre}'"
        registrar_bitacora(
                request=self.request, 
                usuario=self.request.user, 
                accion="CREAR", 
                descripcion=descripcion,
                modulo="Administracion"
        )
    
    def perform_update(self, serializer):
        instance = self.get_object()
        username_original = instance.username
        email_original = instance.email
        rol_original = instance.groups.first()
        rol_original_nombre = rol_original.name if rol_original else 'Sin rol'
        instance = serializer.save()
        rol_nuevo = instance.groups.first()
        rol_nuevo_nombre = rol_nuevo.name if rol_nuevo else 'Sin rol'
        cambios = []
        if instance.username != username_original:
            cambios.append(f"username: '{username_original}' → '{instance.username}'")
        if instance.email != email_original:
            cambios.append(f"email: '{email_original}' → '{instance.email}'")
        if rol_original_nombre != rol_nuevo_nombre:
            cambios.append(f"rol: '{rol_original_nombre}' → '{rol_nuevo_nombre}'")
        
        descripcion = f"Usuario '{instance.username}' actualizado"
        if cambios:
            descripcion += f". Cambios: {', '.join(cambios)}"
        else:
            descripcion += ". Sin cambios detectados"
        
        registrar_bitacora(
            request=request, 
            usuario=self.request.user, 
            accion="EDITAR", 
            descripcion=descripcion,
            modulo="Administracion"
        )
    
    def perform_destroy(self, instance):
        username_usuario = instance.username
        email_usuario = instance.email
        rol_info = instance.groups.first()
        rol_nombre = rol_info.name if rol_info else 'Sin rol'
        instance.delete()
        descripcion = f"Usuario '{username_usuario}' eliminado. Tenía email '{email_usuario}' y rol '{rol_nombre}'"
        registrar_bitacora(
            request=self.request, 
            usuario=self.request.user, 
            accion="ELIMINAR", 
            descripcion=descripcion,
            modulo="Administracion"
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"detail": "No se puede eliminar este usuario porque está asociado a otros registros (como un cliente o empleado)."},
                status=status.HTTP_400_BAD_REQUEST
            )

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = RoleSerializer
    
    def perform_create(self, serializer):
        """Crear rol y registrar en bitácora"""
        # Ejecutar la creación original
        instance = serializer.save()
        
        # Registrar en bitácora
        permisos_info = [perm.name for perm in instance.permissions.all()]
        descripcion = f"Rol '{instance.name}' creado con permisos: {', '.join(permisos_info) if permisos_info else 'Sin permisos'}"
        
        registrar_bitacora(
                request=self.request, 
                usuario=self.request.user, 
                accion="CREAR", 
                descripcion=descripcion,
                modulo="Administracion"
        )
    
    def perform_update(self, serializer):
        """Actualizar rol y registrar en bitácora"""
        # Guardar datos originales para comparación
        instance = self.get_object()
        nombre_original = instance.name
        permisos_originales = set(instance.permissions.values_list('name', flat=True))
        
        # Ejecutar la actualización original
        instance = serializer.save()
        
        # Obtener nuevos permisos
        permisos_nuevos = set(instance.permissions.values_list('name', flat=True))
        
        # Crear descripción detallada
        permisos_agregados = permisos_nuevos - permisos_originales
        permisos_removidos = permisos_originales - permisos_nuevos
        
        descripcion = f"Rol '{instance.name}' actualizado"
        if permisos_agregados:
            descripcion += f". Permisos agregados: {', '.join(permisos_agregados)}"
        if permisos_removidos:
            descripcion += f". Permisos removidos: {', '.join(permisos_removidos)}"
        if not permisos_agregados and not permisos_removidos:
            descripcion += ". Sin cambios en permisos"
        
        registrar_bitacora(
                request=self.request, 
                usuario=self.request.user, 
                accion="EDITAR", 
                descripcion=descripcion,
                modulo="Administracion"
        )
    
    def perform_destroy(self, instance):
        """Eliminar rol y registrar en bitácora"""
        # Guardar información antes de eliminar
        nombre_rol = instance.name
        permisos_info = [perm.name for perm in instance.permissions.all()]
        
        # Ejecutar la eliminación original
        instance.delete()
        
        # Registrar en bitácora
        descripcion = f"Rol '{nombre_rol}' eliminado. Tenía permisos: {', '.join(permisos_info) if permisos_info else 'Sin permisos'}"
        
        registrar_bitacora(
                request=self.request, 
                usuario=self.request.user, 
                accion="ELIMINAR", 
                descripcion=descripcion,
                modulo="Administracion"
        )

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer

class DepartamentoViewSet(viewsets.ModelViewSet):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer

class CiudadViewSet(viewsets.ModelViewSet):
    queryset = Ciudad.objects.all()
    serializer_class = CiudadSerializer

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    
    def perform_create(self, serializer):
        cliente_guardado = serializer.save(usuario=self.request.user)
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="CREAR CLIENTE",
            descripcion=f"Se creó el cliente: {cliente_guardado.nombre}",
            modulo="Clientes"
        )
    
    def perform_update(self, serializer):
        cliente_original = self.get_object()
        nombre_original = cliente_original.nombre
        
        cliente_actualizado = serializer.save()
        
        cambios = []
        if cliente_actualizado.nombre != nombre_original:
            cambios.append(f"nombre: '{nombre_original}' → '{cliente_actualizado.nombre}'")
        
        descripcion = f"Se actualizó el cliente: {cliente_actualizado.nombre}"
        if cambios:
            descripcion += f". Cambios: {', '.join(cambios)}"
        else:
            descripcion += ". Sin cambios detectados"
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="EDITAR",
            descripcion=descripcion,
            modulo="Clientes"
        )

    def perform_destroy(self, instance):
        """Eliminar cliente y registrar en bitácora"""
        nombre_cliente = instance.nombre
        
        instance.delete()
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="ELIMINAR CLIENTE",
            descripcion=f"Se eliminó el cliente: {nombre_cliente}",
            modulo="Clientes"
        )

class RegistroBitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegistroBitacora.objects.all()
    serializer_class = RegistroBitacoraSerializer

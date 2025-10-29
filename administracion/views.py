from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
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



# cart/views.py completo
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers.serializers_cart import CartSerializer, AddCartItemSerializer
from .models import Catalogo
from django.contrib.auth import get_user_model

class CartViewSet(viewsets.GenericViewSet):
    #permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_cart(self):
        # Método auxiliar para no repetir código
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        """Ver mi carrito actual"""
        cart = self.get_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], serializer_class=AddCartItemSerializer)
    def add_item(self, request):
        """
        Añadir un ítem al carrito.
        Ruta: POST /api/cart/add_item/
        Body: { "catalogo_id": 10, "quantity": 2 }
        """
        cart = self.get_cart()
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        catalogo = get_object_or_404(Catalogo, pk=serializer.validated_data['catalogo_id'])
        quantity = serializer.validated_data['quantity']

        # Lógica de update_or_create que vimos antes
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            catalogo=catalogo,
            defaults={'quantity': quantity}
        )

        if not created:
            # Si ya existía, sumamos la cantidad
            cart_item.quantity += quantity
            cart_item.save()

        # Devolvemos el carrito actualizado completo
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='update_item/(?P<item_id>[^/.]+)')
    def update_item_quantity(self, request, item_id=None):
        """
        Actualizar la cantidad de un ítem específico.
        Ruta: PATCH /api/cart/update_item/{item_id}/
        Body: { "quantity": 5 }
        """
        cart = self.get_cart()
        # Aseguramos que el ítem pertenezca al carrito del usuario actual
        cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)

        quantity = int(request.data.get('quantity', 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            # Si envían cantidad 0 o menor, lo borramos
            cart_item.delete()

        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['delete'], url_path='remove_item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """
        Eliminar un ítem del carrito.
        Ruta: DELETE /api/cart/remove_item/{item_id}/
        """
        cart = self.get_cart()
        cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        cart_item.delete()
        
        return Response(CartSerializer(cart).data)

# Create your views here.

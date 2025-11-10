# cart/models.py
import uuid
from django.db import models
from django.conf import settings
from catalogo.models import Catalogo # Importa tu modelo Catalogo

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return sum([item.subtotal for item in self.items.all()])

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    # AQUÍ EL CAMBIO CLAVE: Vinculamos con Catalogo, no con Producto específico
    catalogo = models.ForeignKey(Catalogo, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = [['cart', 'catalogo']]

    @property
    def subtotal(self):
        # Usamos el precio del catálogo
        return self.catalogo.precio * self.quantity

# Create your models here.

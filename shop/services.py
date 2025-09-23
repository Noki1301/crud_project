from decimal import Decimal
from typing import Optional

from django.db import models, transaction
from django.utils import timezone

from .models import Cart, CartItem, Coupon, Product


class CartManager:
    def __init__(self, *, user=None, session_key: Optional[str] = None):
        self.user = user if user and user.is_authenticated else None
        self.session_key = session_key
        self.cart = self._get_or_create_cart()

    def _get_or_create_cart(self) -> Cart:
        if self.user:
            cart, _ = Cart.objects.get_or_create(user=self.user)
            if self.session_key and not cart.session_key:
                cart.session_key = self.session_key
                cart.save(update_fields=["session_key"])
            return cart

        if not self.session_key:
            raise ValueError("Session key is required for anonymous carts")

        cart, _ = Cart.objects.get_or_create(session_key=self.session_key, user=None)
        return cart

    def add_product(self, product: Product, quantity: int = 1):
        if quantity < 1:
            quantity = 1
        item, created = self.cart.items.get_or_create(
            product=product, defaults={"quantity": quantity, "unit_price": product.price}
        )
        if not created:
            item.quantity += quantity
            item.unit_price = product.price
            item.save(update_fields=["quantity", "unit_price", "updated_at"])
        return item

    def update_quantity(self, product: Product, quantity: int):
        try:
            item = self.cart.items.get(product=product)
        except CartItem.DoesNotExist:
            return None
        if quantity < 1:
            item.delete()
        else:
            item.quantity = quantity
            item.unit_price = product.price
            item.save(update_fields=["quantity", "unit_price", "updated_at"])
        return item

    def remove_product(self, product: Product):
        self.cart.items.filter(product=product).delete()

    def apply_coupon(self, code: str) -> Optional[Coupon]:
        now = timezone.now()
        coupon = (
            Coupon.objects.filter(
                code__iexact=code,
                is_active=True,
                active_from__lte=now,
                active_to__gte=now,
            )
            .exclude(usage_limit__isnull=False, used_count__gte=models.F("usage_limit"))
            .first()
        )
        if coupon:
            self.cart.coupon = coupon
            self.cart.save(update_fields=["coupon", "updated_at"])
        return coupon

    def totals(self):
        subtotal = self.cart.subtotal()
        discount = Decimal("0.00")
        if self.cart.coupon:
            if self.cart.coupon.type == Coupon.CouponType.PERCENT:
                discount = subtotal * (self.cart.coupon.value / Decimal("100"))
            else:
                discount = self.cart.coupon.value
            discount = min(discount, subtotal)
        total = subtotal - discount
        return {"subtotal": subtotal, "discount": discount, "total": total}


@transaction.atomic
def checkout_cart(*, cart: Cart, address, user, notes: str = ""):
    from .models import Order, OrderItem

    totals = CartManager(user=user, session_key=cart.session_key).totals()
    order = Order.objects.create(
        user=user,
        status=Order.Status.PENDING,
        subtotal=totals["subtotal"],
        discount=totals["discount"],
        total=totals["total"],
        shipping_address=address,
        coupon=cart.coupon,
        notes=notes,
    )

    items = []
    for item in cart.items.select_related("product"):
        if item.product.stock < item.quantity:
            raise ValueError(f"{item.product.name} da yetarli zaxira yo'q")
        item.product.stock -= item.quantity
        item.product.save(update_fields=["stock", "updated_at"])
        items.append(
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
        )

    OrderItem.objects.bulk_create(items)
    cart.items.all().delete()
    cart.coupon = None
    cart.save(update_fields=["coupon", "updated_at"])
    return order

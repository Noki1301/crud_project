from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

User = settings.AUTH_USER_MODEL

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_descendants(self, include_self: bool = False):
        descendants = []
        queue = list(self.children.filter(is_active=True))
        while queue:
            node = queue.pop(0)
            descendants.append(node)
            queue.extend(node.children.filter(is_active=True))
        if include_self:
            descendants.append(self)
        return descendants


class Product(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))], blank=True, null=True
    )
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def available_stock(self):
        return self.stock - sum(item.quantity for item in self.commitments.all())


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt = models.CharField(max_length=140, blank=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Image for {self.product.name}"


class InventoryCommitment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="commitments")
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["expires_at"])]

    def __str__(self):
        return f"{self.quantity} reserved of {self.product}"


class Coupon(TimeStampedModel):
    class CouponType(models.TextChoices):
        PERCENT = "percent", "Percent"
        FIXED = "fixed", "Fixed amount"

    code = models.CharField(max_length=30, unique=True)
    type = models.CharField(max_length=10, choices=CouponType.choices)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    active_from = models.DateTimeField()
    active_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class Address(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=80)
    region = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, default="UZ")
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.city})"


class Cart(TimeStampedModel):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, blank=True)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"], name="unique_cart_per_user", condition=models.Q(user__isnull=False)
            )
        ]

    def __str__(self):
        return f"Cart #{self.pk}"

    def subtotal(self):
        return sum(item.subtotal for item in self.items.select_related("product"))


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = (("cart", "product"),)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_address = models.ForeignKey(
        Address, on_delete=models.PROTECT, related_name="shipping_orders"
    )
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Order #{self.pk}"


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.INITIATED)
    raw_payload = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Payment for order #{self.order_id}"

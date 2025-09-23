from django.contrib import admin

from . import models


class ProductImageInline(admin.TabularInline):
    model = models.ProductImage
    extra = 1


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "created_at")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "parent__name")


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_active", "featured")
    list_filter = ("is_active", "featured", "category")
    search_fields = ("name", "category__name")
    inlines = [ProductImageInline]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(models.Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "type", "value", "active_from", "active_to", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("code",)


@admin.register(models.Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "city", "country", "is_default")
    list_filter = ("country", "is_default")
    search_fields = ("full_name", "user__username", "city")


class CartItemInline(admin.TabularInline):
    model = models.CartItem
    extra = 0


@admin.register(models.Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "coupon", "updated_at")
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 0


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__username")
    inlines = [OrderItemInline]


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "amount", "status", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("order__id", "provider")


@admin.register(models.InventoryCommitment)
class InventoryCommitmentAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "expires_at")
    list_filter = ("expires_at",)
    search_fields = ("product__name",)

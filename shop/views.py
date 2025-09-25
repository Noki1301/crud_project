from __future__ import annotations

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from .forms import (
    AddToCartForm,
    AddressForm,
    CheckoutNotesForm,
    CouponApplyForm,
    ProfileUpdateForm,
    StoreRegistrationForm,
)
from .models import Cart, CartItem, Category, Order, Product
from .services import CartManager, checkout_cart


class StoreBaseMixin:
    def ensure_session(self):
        if not self.request.session.session_key:
            self.request.session.create()
        return self.request.session.session_key

    def get_cart_manager(self) -> CartManager:
        session_key = self.ensure_session()
        return CartManager(user=self.request.user, session_key=session_key)


class HomeView(StoreBaseMixin, TemplateView):
    template_name = "store/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        featured_products = (
            Product.objects.filter(is_active=True, featured=True)
            .select_related("category")
            .prefetch_related("images")
            [:8]
        )
        latest_products = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .order_by("-created_at")
            [:12]
        )
        context.update(
            {
                "featured_products": featured_products,
                "latest_products": latest_products,
                "categories": Category.objects.filter(is_active=True, parent__isnull=True),
            }
        )
        return context


class ProductListView(StoreBaseMixin, ListView):
    template_name = "store/product_list.html"
    model = Product
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("images")
        )
        category_slug = self.kwargs.get("category_slug")
        if category_slug:
            self.category = get_object_or_404(Category, slug=category_slug, is_active=True)
            queryset = queryset.filter(category__in=self.category.get_descendants(include_self=True))
        else:
            self.category = None
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = getattr(self, "category", None)
        context["search_query"] = self.request.GET.get("q", "")
        context["categories"] = Category.objects.filter(is_active=True, parent__isnull=True)
        context["cart"] = self.get_cart_manager().cart
        return context


class ProductDetailView(StoreBaseMixin, DetailView):
    template_name = "store/product_detail.html"
    model = Product
    context_object_name = "product"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("images")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["add_to_cart_form"] = AddToCartForm()
        context["related_products"] = (
            Product.objects.filter(category=self.object.category, is_active=True)
            .exclude(pk=self.object.pk)[:4]
        )
        return context


class CartView(StoreBaseMixin, TemplateView):
    template_name = "store/cart.html"

    def post(self, request, *args, **kwargs):
        manager = self.get_cart_manager()
        action = request.POST.get("action")
        product_id = request.POST.get("product_id")
        if product_id:
            product = get_object_or_404(Product, pk=product_id, is_active=True)
        else:
            product = None
        if action == "update" and product:
            qty = max(int(request.POST.get("quantity", 1)), 1)
            manager.update_quantity(product, qty)
            messages.success(request, "Savatcha yangilandi.")
        elif action == "remove" and product:
            manager.remove_product(product)
            messages.info(request, "Mahsulot savatchadan o'chirildi.")
        elif action == "coupon":
            form = CouponApplyForm(request.POST)
            if form.is_valid():
                coupon = manager.apply_coupon(form.cleaned_data["code"])
                if coupon:
                    messages.success(request, "Promo-kod qo'llandi.")
                else:
                    messages.error(request, "Promo-kod topilmadi yoki muddati o'tgan.")
        return redirect("store:cart")

    def get_context_data(self, **kwargs):
        manager = self.get_cart_manager()
        context = super().get_context_data(**kwargs)
        context["cart"] = manager.cart
        context["items"] = manager.cart.items.select_related("product", "product__category")
        context["totals"] = manager.totals()
        context["coupon_form"] = CouponApplyForm()
        return context


@method_decorator(login_required, name="dispatch")
class CheckoutView(StoreBaseMixin, TemplateView):
    template_name = "store/checkout.html"

    def post(self, request, *args, **kwargs):
        manager = self.get_cart_manager()
        cart = manager.cart
        if not cart.items.exists():
            messages.warning(request, "Savatcha bo'sh.")
            return redirect("store:cart")

        address_form = AddressForm(request.POST, prefix="address")
        notes_form = CheckoutNotesForm(request.POST, prefix="notes")
        if address_form.is_valid() and notes_form.is_valid():
            address = address_form.save(commit=False)
            address.user = request.user
            if address.is_default:
                address.__class__.objects.filter(user=request.user, is_default=True).update(is_default=False)
            address.save()
            try:
                order = checkout_cart(
                    cart=cart, address=address, user=request.user, notes=notes_form.cleaned_data.get("notes", "")
                )
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("store:cart")
            messages.success(request, "Buyurtma muvaffaqiyatli yaratildi.")
            return redirect("store:order_success", order_pk=order.pk)

        context = self.get_context_data(address_form=address_form, notes_form=notes_form)
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        manager = self.get_cart_manager()
        context = super().get_context_data(**kwargs)
        context.setdefault("address_form", AddressForm(prefix="address"))
        context.setdefault("notes_form", CheckoutNotesForm(prefix="notes"))
        context["cart"] = manager.cart
        context["items"] = manager.cart.items.select_related("product")
        context["totals"] = manager.totals()
        return context


@method_decorator(login_required, name="dispatch")
class OrderSuccessView(TemplateView):
    template_name = "store/order_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order_pk"] = self.kwargs.get("order_pk")
        return context


class AddToCartView(StoreBaseMixin, View):
    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, pk=kwargs.get("pk"), is_active=True)
        form = AddToCartForm(request.POST)
        if form.is_valid():
            manager = self.get_cart_manager()
            manager.add_product(product, form.cleaned_data["quantity"])
            messages.success(request, "Mahsulot savatchaga qo'shildi.")
        else:
            messages.error(request, "Noto'g'ri miqdor kerak.")
        return redirect(request.META.get("HTTP_REFERER", reverse("store:product_detail", args=[product.slug])))


class QuickAddToCartView(StoreBaseMixin, View):
    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, pk=kwargs.get("pk"), is_active=True)
        manager = self.get_cart_manager()
        manager.add_product(product, 1)
        messages.success(request, "Mahsulot 1 dona savatchaga qo'shildi.")
        return redirect("store:cart")


class StoreLoginView(View):
    template_name = "store/auth_login.html"

    def get_form(self, request, data=None):
        from django.contrib.auth.forms import AuthenticationForm

        form = AuthenticationForm(request, data=data)
        form.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Login"})
        form.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Parol"})
        return form

    def get(self, request):
        form = self.get_form(request)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.get_form(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Xush kelibsiz!")
            return redirect(request.GET.get("next") or "store:account_dashboard")
        return render(request, self.template_name, {"form": form})


class StoreRegisterView(View):
    template_name = "store/auth_register.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "Siz allaqachon tizimdasiz.")
            return redirect("store:account_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = StoreRegistrationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = StoreRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.")
            return redirect("store:account_dashboard")
        return render(request, self.template_name, {"form": form})


class StoreLogoutView(View):
    def post(self, request):
        from django.contrib.auth import logout

        logout(request)
        messages.info(request, "Tizimdan chiqdingiz.")
        return redirect("store:home")

    def get(self, request):
        return redirect("store:home")


class AccountBaseView(StoreBaseMixin, LoginRequiredMixin):
    login_url = reverse_lazy("store:login")
    redirect_field_name = "next"


class AccountDashboardView(AccountBaseView, TemplateView):
    template_name = "store/account/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_qs = (
            Order.objects.filter(user=self.request.user)
            .select_related("shipping_address")
            .order_by("-created_at")
        )
        revenue = (
            order_qs.filter(status__in=[Order.Status.PAID, Order.Status.COMPLETED])
            .aggregate(sum_total=Sum("total"))
            .get("sum_total")
            or Decimal("0.00")
        )
        context.update(
            {
                "recent_orders": order_qs[:5],
                "orders_count": order_qs.count(),
                "pending_orders": order_qs.filter(status=Order.Status.PENDING).count(),
                "total_spent": revenue,
                "account_section": "dashboard",
            }
        )
        return context


class AccountOrderListView(AccountBaseView, ListView):
    template_name = "store/account/orders.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("shipping_address", "coupon")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["account_section"] = "orders"
        return context


class AccountOrderDetailView(AccountBaseView, DetailView):
    model = Order
    template_name = "store/account/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("shipping_address", "coupon")
            .prefetch_related("items__product")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.select_related("product")
        context["account_section"] = "orders"
        return context


class AccountProfileUpdateView(AccountBaseView, View):
    template_name = "store/account/profile.html"

    def get(self, request):
        form = ProfileUpdateForm(instance=request.user)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "addresses": request.user.addresses.all(),
                "account_section": "profile",
            },
        )

    def post(self, request):
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil ma'lumotlari yangilandi.")
            return redirect("store:account_profile")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "addresses": request.user.addresses.all(),
                "account_section": "profile",
            },
        )


class AccountPasswordChangeView(AccountBaseView, PasswordChangeView):
    template_name = "store/account/password_change.html"
    success_url = reverse_lazy("store:account_dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Parol muvaffaqiyatli yangilandi.")
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            classes = field.widget.attrs.get("class", "").split()
            if "form-control" not in classes:
                classes.append("form-control")
            field.widget.attrs["class"] = " ".join(classes).strip()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["account_section"] = "security"
        return context

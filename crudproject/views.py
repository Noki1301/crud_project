from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.db.models import Q, Count, Sum, ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)

from .forms import (
    UserForm,
    UserFilterForm,
    CategoryForm,
    ProductAdminForm,
    ProductFilterForm,
    OrderStatusForm,
)
from .mixins import StaffRequiredMixin
from shop.models import Category, Product, Order

User = get_user_model()


class DashboardLoginView(LoginView):
    template_name = "dashboard/auth_login.html"
    form_class = AuthenticationForm
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        if request.session.get("dashboard_user_id"):
            next_url = request.GET.get("next")
            return redirect(next_url or reverse("dashboard:home"))
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            classes = field.widget.attrs.get('class', '').split()
            if 'form-control' not in classes:
                classes.append('form-control')
            field.widget.attrs['class'] = ' '.join(filter(None, classes))
        return form

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_staff:
            form.add_error(None, "Sizga admin panelga kirish huquqi berilmagan.")
            return self.form_invalid(form)
        self.request.session["dashboard_user_id"] = user.pk
        self.request.session.modified = True
        messages.success(self.request, "Admin panelga xush kelibsiz!")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.request.GET.get("next") or reverse_lazy("dashboard:home")


class DashboardLogoutView(View):
    def post(self, request, *args, **kwargs):
        request.session.pop("dashboard_user_id", None)
        messages.info(request, "Admin paneldan chiqdingiz.")
        return redirect("dashboard:login")

    def get(self, request, *args, **kwargs):
        request.session.pop("dashboard_user_id", None)
        messages.info(request, "Admin paneldan chiqdingiz.")
        return redirect("dashboard:login")


class UserListView(StaffRequiredMixin, ListView):
    model = User
    template_name = "user_admin_view/user_list.html"
    context_object_name = "users"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()

        if q:
            queryset = queryset.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )

        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = UserFilterForm(self.request.GET or None)
        context["active_filter"] = {
            "q": self.request.GET.get("q", "").strip(),
            "status": self.request.GET.get("status", "").strip(),
        }
        context["stats"] = {
            "total": User.objects.count(),
            "active": User.objects.filter(is_active=True).count(),
            "inactive": User.objects.filter(is_active=False).count(),
            "filtered": context["paginator"].count if "paginator" in context else context["object_list"].count(),
        }
        return context


class UserDetailView(StaffRequiredMixin, DetailView):
    model = User
    template_name = "user_admin_view/user_detail.html"
    context_object_name = "user"


class UserCreateView(StaffRequiredMixin, CreateView):
    model = User
    template_name = "user_admin_view/user_form.html"
    form_class = UserForm
    success_url = reverse_lazy("dashboard:user_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.object.has_usable_password():
            self.object.set_unusable_password()
            self.object.save(update_fields=['password'])
        messages.success(self.request, f"User '{self.object.username}' was created successfully.")
        return response


class UserUpdateView(StaffRequiredMixin, UpdateView):
    model = User
    template_name = "user_admin_view/user_form.html"
    form_class = UserForm
    success_url = reverse_lazy("dashboard:user_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"User '{self.object.username}' was updated successfully.")
        return response


class UserDeleteView(StaffRequiredMixin, DeleteView):
    model = User
    template_name = "user_admin_view/user_confirm_delete.html"
    context_object_name = "user"
    success_url = reverse_lazy("dashboard:user_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        username = self.object.username
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"User '{username}' was deleted successfully.")
        return response


class DashboardHomeView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_qs = Order.objects.select_related("user")
        total_orders = order_qs.count()
        total_revenue = order_qs.filter(status__in=[Order.Status.PAID, Order.Status.COMPLETED]).aggregate(sum=Sum("total"))
        context.update(
            {
                "stats": {
                    "users": User.objects.count(),
                    "products": Product.objects.count(),
                    "categories": Category.objects.count(),
                    "orders": total_orders,
                    "revenue": total_revenue.get("sum") or 0,
                },
                "latest_orders": order_qs.order_by("-created_at")[:6],
                "low_stock": Product.objects.filter(stock__lte=5, is_active=True)[:5],
            }
        )
        return context


class CategoryAdminListView(StaffRequiredMixin, ListView):
    model = Category
    template_name = "dashboard/category_list.html"
    context_object_name = "categories"
    paginate_by = 12

    def get_queryset(self):
        return (
            Category.objects.select_related("parent")
            .annotate(product_count=Count("products"))
            .order_by("name")
        )


class CategoryAdminCreateView(StaffRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "dashboard/category_form.html"
    success_url = reverse_lazy("dashboard:category_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["parent"].queryset = Category.objects.filter(is_active=True)
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Kategoriya muvaffaqiyatli yaratildi.")
        return response


class CategoryAdminUpdateView(StaffRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "dashboard/category_form.html"
    success_url = reverse_lazy("dashboard:category_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["parent"].queryset = Category.objects.filter(is_active=True).exclude(pk=self.object.pk)
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Kategoriya yangilandi.")
        return response


class CategoryAdminDeleteView(StaffRequiredMixin, DeleteView):
    model = Category
    template_name = "dashboard/category_confirm_delete.html"
    success_url = reverse_lazy("dashboard:category_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Kategoriya o'chirildi")
            return response
        except ProtectedError:
            messages.error(request, "Ushbu kategoriyani o'chirib bo'lmaydi. Avval bog'langan mahsulotlarni o'zgartiring.")
            return redirect("dashboard:category_list")


class ProductAdminListView(StaffRequiredMixin, ListView):
    model = Product
    template_name = "dashboard/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.select_related("category").prefetch_related("images")
        self.filter_form = ProductFilterForm(self.request.GET or None)
        if self.filter_form.is_valid():
            q = self.filter_form.cleaned_data.get("q")
            status = self.filter_form.cleaned_data.get("status")
            category = self.filter_form.cleaned_data.get("category")
            if q:
                queryset = queryset.filter(name__icontains=q)
            if status == "active":
                queryset = queryset.filter(is_active=True)
            elif status == "inactive":
                queryset = queryset.filter(is_active=False)
            if category:
                queryset = queryset.filter(category=category)
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["categories"] = Category.objects.filter(is_active=True)
        context["total_products"] = Product.objects.count()
        context["active_products"] = Product.objects.filter(is_active=True).count()
        return context


class ProductAdminCreateView(StaffRequiredMixin, CreateView):
    model = Product
    form_class = ProductAdminForm
    template_name = "dashboard/product_form.html"
    success_url = reverse_lazy("dashboard:product_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("default_image", None)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Mahsulot qo'shildi.")
        return response


class ProductAdminUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    form_class = ProductAdminForm
    template_name = "dashboard/product_form.html"
    success_url = reverse_lazy("dashboard:product_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        default_image = self.object.images.filter(is_default=True).first() or self.object.images.first()
        context["default_image"] = default_image
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Mahsulot yangilandi.")
        return response


class ProductAdminDeleteView(StaffRequiredMixin, DeleteView):
    model = Product
    template_name = "dashboard/product_confirm_delete.html"
    success_url = reverse_lazy("dashboard:product_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Mahsulot o'chirildi.")
            return response
        except ProtectedError:
            messages.error(request, "Mahsulot buyurtmalarda mavjud. Avval tegishli buyurtmalarni tekshiring.")
            return redirect("dashboard:product_list")


class OrderAdminListView(StaffRequiredMixin, ListView):
    model = Order
    template_name = "dashboard/order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.select_related("user", "shipping_address", "coupon")
        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get("status", "").strip()
        context["status"] = status
        context["status_summary"] = [
            {"value": value, "label": label, "count": Order.objects.filter(status=value).count()}
            for value, label in Order.Status.choices
        ]
        return context


class OrderAdminDetailView(StaffRequiredMixin, DetailView):
    model = Order
    template_name = "dashboard/order_detail.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.select_related("product")
        context["status_form"] = OrderStatusForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = OrderStatusForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            messages.success(request, "Buyurtma holati yangilandi.")
            return redirect("dashboard:order_detail", pk=self.object.pk)
        context = self.get_context_data()
        context["status_form"] = form
        return self.render_to_response(context)

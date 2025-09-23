from django.urls import path

app_name = "dashboard"
from .views import (
    DashboardHomeView,
    UserListView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView,
    UserDetailView,
    CategoryAdminListView,
    CategoryAdminCreateView,
    CategoryAdminUpdateView,
    CategoryAdminDeleteView,
    ProductAdminListView,
    ProductAdminCreateView,
    ProductAdminUpdateView,
    ProductAdminDeleteView,
    OrderAdminListView,
    OrderAdminDetailView,
)

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="home"),
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/create/", UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/update/", UserUpdateView.as_view(), name="user_update"),
    path("users/<int:pk>/delete/", UserDeleteView.as_view(), name="user_delete"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user_detail"),
    path("categories/", CategoryAdminListView.as_view(), name="category_list"),
    path("categories/create/", CategoryAdminCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/update/", CategoryAdminUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", CategoryAdminDeleteView.as_view(), name="category_delete"),
    path("products/", ProductAdminListView.as_view(), name="product_list"),
    path("products/create/", ProductAdminCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/update/", ProductAdminUpdateView.as_view(), name="product_update"),
    path("products/<int:pk>/delete/", ProductAdminDeleteView.as_view(), name="product_delete"),
    path("orders/", OrderAdminListView.as_view(), name="order_list"),
    path("orders/<int:pk>/", OrderAdminDetailView.as_view(), name="order_detail"),
]

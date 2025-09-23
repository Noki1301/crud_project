from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("login/", views.StoreLoginView.as_view(), name="login"),
    path("logout/", views.StoreLogoutView.as_view(), name="logout"),
    path("catalog/", views.ProductListView.as_view(), name="product_list"),
    path("catalog/<slug:category_slug>/", views.ProductListView.as_view(), name="product_list_by_category"),
    path("product/<slug:slug>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("product/<int:pk>/add/", views.AddToCartView.as_view(), name="add_to_cart"),
    path("product/<int:pk>/quick-add/", views.QuickAddToCartView.as_view(), name="quick_add_to_cart"),
    path("cart/", views.CartView.as_view(), name="cart"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("order-success/<int:order_pk>/", views.OrderSuccessView.as_view(), name="order_success"),
]

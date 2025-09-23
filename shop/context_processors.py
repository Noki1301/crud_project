from .services import CartManager


def cart(request):
    try:
        manager = CartManager(user=request.user, session_key=request.session.session_key)
    except Exception:
        if not request.session.session_key:
            request.session.create()
        manager = CartManager(user=request.user, session_key=request.session.session_key)
    return {"cart": manager.cart}

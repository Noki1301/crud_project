from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse


User = get_user_model()


class StaffRequiredMixin:
    """Restrict dashboard views to staff users with dedicated admin session."""

    def dispatch(self, request, *args, **kwargs):
        dashboard_user_id = request.session.get("dashboard_user_id")
        if not dashboard_user_id:
            next_param = quote(request.get_full_path())
            return redirect(f"{reverse('dashboard:login')}?next={next_param}")

        user = User.objects.filter(pk=dashboard_user_id, is_staff=True, is_active=True).first()
        if not user:
            request.session.pop("dashboard_user_id", None)
            messages.error(request, "Admin sessiyasi amal qilmayapti. Iltimos, qayta kiring.")
            return redirect("dashboard:login")

        request.dashboard_user = user
        # Shadow the request user inside dashboard only
        request.user = user
        return super().dispatch(request, *args, **kwargs)

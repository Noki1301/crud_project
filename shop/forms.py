from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Address

User = get_user_model()


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
    )


class CouponApplyForm(forms.Form):
    code = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Promo code"}),
    )


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "region",
            "postal_code",
            "country",
            "is_default",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "line1": forms.TextInput(attrs={"class": "form-control"}),
            "line2": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control", "placeholder": "UZ"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CheckoutNotesForm(forms.Form):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Order notes"}),
    )


class StoreRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ismingiz"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Familiyangiz"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "first_name": "Ism",
            "last_name": "Familiya",
            "username": "Foydalanuvchi nomi",
            "email": "Email manzil",
            "password1": "Parol",
            "password2": "Parolni tasdiqlang",
        }
        placeholders = {
            "first_name": "Ismingiz",
            "last_name": "Familiyangiz",
            "username": "foydalanuvchi",
            "email": "email@example.com",
            "password1": "Kamida 8 ta belgi",
            "password2": "Yangi parolni qayta kiriting",
        }
        for name, field in self.fields.items():
            classes = field.widget.attrs.get("class", "").split()
            if "form-control" not in classes:
                classes.append("form-control")
            if name in self.errors:
                classes.append("is-invalid")
            field.widget.attrs["class"] = " ".join(classes).strip()
            field.widget.attrs.setdefault("placeholder", placeholders.get(name, ""))
            field.label = labels.get(name, field.label)
            field.help_text = ""
            field.widget.attrs.setdefault("autocomplete", name)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu email allaqachon ro'yxatdan o'tgan.")
        return email


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ismingiz"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Familiyangiz"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "email@example.com"}),
        }
        labels = {
            "first_name": "Ism",
            "last_name": "Familiya",
            "email": "Email manzil",
        }
        help_texts = {field: "" for field in fields}

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email majburiy.")
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Bu email boshqa foydalanuvchi tomonidan ishlatilmoqda.")
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("autocomplete", name)

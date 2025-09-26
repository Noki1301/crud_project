from django import forms
from django.contrib.auth import get_user_model

from shop.models import Category, Product, ProductImage, Order

User = get_user_model()


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_active", "is_staff"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError('Email is required.')
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This email is already in use.')
        return email


class UserFilterForm(forms.Form):
    q = forms.CharField(
        label="Search",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search by username, name or email"}),
    )
    status = forms.ChoiceField(
        label="Status",
        required=False,
        choices=(
            ("", "All"),
            ("active", "Active"),
            ("inactive", "Inactive"),
        ),
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class CategoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Category.objects.filter(is_active=True)

    class Meta:
        model = Category
        fields = ["name", "parent", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ProductAdminForm(forms.ModelForm):
    main_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "stock",
            "is_active",
            "featured",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "short_description": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "compare_at_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def save(self, commit=True):
        product = super().save(commit=commit)
        image = self.cleaned_data.get("main_image")
        if image:
            ProductImage.objects.update_or_create(
                product=product,
                is_default=True,
                defaults={"image": image, "alt": product.name},
            )
        elif image is False:
            ProductImage.objects.filter(product=product, is_default=True).delete()
        return product


class ProductFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Mahsulot nomi"}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=(("", "Holati"), ("active", "Faol"), ("inactive", "Faol emas")),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "notes"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

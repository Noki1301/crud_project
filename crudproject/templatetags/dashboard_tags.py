from django import template

register = template.Library()


@register.filter
def in_list(value, arg):
    if value is None:
        return False
    items = [item.strip() for item in str(arg).split(",") if item.strip()]
    return value in items

from django import template

register = template.Library()

@register.filter
def divide(value, arg):
    try:
        return int(value) / int(arg) * 100
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

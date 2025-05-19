from django import template
from django.template.defaultfilters import register

@register.filter(name='max')
def max_value(value, arg):
    """Returns the maximum of the value and the argument."""
    try:
        return max(float(value), float(arg))
    except (ValueError, TypeError):
        return value

@register.filter(name='sub')
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='intdiv')
def intdiv(value, arg):
    """Perform integer division of value by arg."""
    try:
        return int(float(value) // float(arg))
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='mul')
def mul(value, arg):
    """Multiply the value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='sum')
def sum_values(iterable):
    """Sum all values in an iterable."""
    try:
        return sum(float(x) for x in iterable if x is not None)
    except (ValueError, TypeError):
        return 0

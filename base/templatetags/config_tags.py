from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key)

@register.filter
def filter_by_module(mappings, module_name):
    if not mappings:
        return []
    return [m for m in mappings if m.zoho_module == module_name]

@register.filter
def split(value, arg):
    return value.split(arg)

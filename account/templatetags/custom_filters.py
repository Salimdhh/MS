# C:\Users\PC\Desktop\Warehouse\Inventory\account\templatetags\custom_filters.py
from django import template

register = template.Library()

@register.filter(name='attr')
def add_attr(field, css):
    attrs = {}
    existing_classes = field.field.widget.attrs.get('class', '').split()

    if field.id_for_label:
        attrs['id'] = field.id_for_label

    for pair in css.split(','):
        try:
            key, value = pair.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key == 'class':
                existing_classes.extend(value.split())
            else:
                attrs[key] = value
        except ValueError:
            print(f"Warning: Malformed attribute pair in custom_filters.py: {pair}")
            continue

    if existing_classes:
        attrs['class'] = ' '.join(set(existing_classes))

    return field.as_widget(attrs=attrs)

# accounts/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """
    يضيف فئات CSS إلى حقل النموذج.
    """
    return value.as_widget(attrs={'class': arg})

# يمكنك إضافة فلاتر أخرى هنا لاحقًا إذا احتجت
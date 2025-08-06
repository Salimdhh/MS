# hr/templatetags/hr_filters.py
from django import template
from datetime import datetime, timedelta

register = template.Library()

@register.filter
def timesince_with_seconds(value, arg):
    """
    Calculates the time difference between two datetime objects
    and returns it in HH:MM:SS format.
    Assumes 'value' is later than 'arg'.
    """
    if not isinstance(value, datetime) or not isinstance(arg, datetime):
        return ""

    diff: timedelta = value - arg
    total_seconds = int(diff.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02}:{minutes:02}:{seconds:02}"

# hr/templatetags/hr_filters.py
# ... (الدوال الأخرى) ...
@register.filter
def add_current_year(value, current_year):
    years = [int(y) for y in value.split(',')]
    if current_year not in years:
        years.append(current_year)
    years.sort(reverse=True) # لترتيب السنوات تنازليًا
    return years

# hr/templatetags/hr_filters.py
from django import template
from datetime import timedelta, datetime

register = template.Library()

@register.filter
def timesince_with_seconds(value, arg=None):
    """
    Calculates the time difference between two datetime objects
    or formats a timedelta object into HH:MM:SS format.
    If arg is provided, calculates diff between value and arg.
    If arg is None, assumes value is a timedelta object.
    """
    if isinstance(value, timedelta):
        diff = value
    elif isinstance(value, datetime) and isinstance(arg, datetime):
        diff = value - arg
    else:
        # يمكنك إرجاع قيمة افتراضية أو رفع خطأ إذا كان النوع غير مدعوم
        return "--:--:--"

    total_seconds = int(diff.total_seconds())

    # التعامل مع المدد السالبة
    if total_seconds < 0:
        sign = "-"
        total_seconds = abs(total_seconds)
    else:
        sign = ""

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{sign}{hours:02}:{minutes:02}:{seconds:02}"

@register.filter
def duration_to_hours(td_object):
    """
    Converts a timedelta object to a decimal representation of hours.
    e.g., timedelta(hours=1, minutes=30) -> 1.5
    """
    if not isinstance(td_object, timedelta):
        return 0.0 # أو يمكنك إرجاع قيمة فارغة مثل '' أو '-'
    
    total_seconds = td_object.total_seconds()
    hours = total_seconds / 3600.0
    return round(hours, 2) # تقريب إلى منزلتين عشريتين
    
@register.filter
def add_current_year(value, current_year):
    """
    Adds the current year to a comma-separated string of years and returns a sorted list.
    """
    years = [int(y) for y in value.split(',')]
    if current_year not in years:
        years.append(current_year)
    years.sort(reverse=True) # لترتيب السنوات تنازليًا
    return years
from datetime import date

from django import template
from django.utils import timezone
from django.utils.timesince import timesince


register = template.Library()

ROMANIAN_MONTHS = (
    "", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
    "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie",
)

ARTICLE_DATE_MONTHS = (
    "", "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
    "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie",
)


@register.filter
def article_date_ro(value):
    """Render article dates as “Astăzi” or a full Romanian calendar date."""
    if not value:
        return ""
    try:
        local_value = timezone.localtime(value) if timezone.is_aware(value) else value
        article_day = local_value.date() if hasattr(local_value, "date") else local_value
    except (AttributeError, TypeError, ValueError):
        return value
    if article_day == timezone.localdate():
        return "Astăzi"
    return f"{article_day.day} {ARTICLE_DATE_MONTHS[article_day.month]} {article_day.year}"


@register.filter
def event_date_ro(value):
    """Render an ISO event date as a full Romanian date."""
    if not value:
        return ""
    try:
        parsed = date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return value
    return f"{parsed.day} {ROMANIAN_MONTHS[parsed.month]} {parsed.year}"


@register.filter
def natural_timesince(value):
    """Render a natural Romanian publication interval."""
    if not value:
        return ""
    interval = timesince(value).replace(", ", " și ", 1)
    interval = interval.replace("1 oră", "o oră").replace("1\xa0oră", "o\xa0oră")
    interval = interval.replace("1 zi", "o zi").replace("1\xa0zi", "o\xa0zi")
    interval = interval.replace("2 zile", "două zile").replace(
        "2\xa0zile", "două\xa0zile"
    )
    if interval in {"0 minute", "0\xa0minute"}:
        return "chiar acum"
    return f"acum {interval}"

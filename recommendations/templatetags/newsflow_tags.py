from datetime import date

from django import template
from django.utils.timesince import timesince


register = template.Library()

ROMANIAN_MONTHS = (
    "", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
    "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie",
)


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
    if interval in {"0 minute", "0\xa0minute"}:
        return "chiar acum"
    return f"acum {interval}"

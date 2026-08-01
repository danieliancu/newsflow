from decimal import Decimal

from django.conf import settings

from .models import AIUsage


MILLION = Decimal("1000000")


def usage_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def record_ai_usage(
    response,
    *,
    model,
    input_rate,
    cached_input_rate,
    output_rate,
    usage_type,
    article=None,
    event=None,
    refresh_run=None,
):
    usage = getattr(response, "usage", None)
    input_tokens = usage_int(getattr(usage, "input_tokens", 0))
    output_tokens = usage_int(getattr(usage, "output_tokens", 0))
    cached_tokens = usage_int(
        getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0)
    )
    regular_tokens = max(0, input_tokens - cached_tokens)
    input_cost = (
        Decimal(regular_tokens) * Decimal(input_rate)
        + Decimal(cached_tokens) * Decimal(cached_input_rate)
    ) / MILLION
    output_cost = Decimal(output_tokens) * Decimal(output_rate) / MILLION
    total_cost = input_cost + output_cost
    gbp_rate = Decimal(settings.OPENAI_USD_TO_GBP_RATE)
    return AIUsage.objects.create(
        article=article,
        event=event,
        refresh_run=refresh_run,
        usage_type=usage_type,
        model=model,
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        output_tokens=output_tokens,
        total_tokens=usage_int(getattr(usage, "total_tokens", 0))
        or input_tokens + output_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=total_cost,
        usd_to_gbp_rate=gbp_rate,
        total_cost_gbp=total_cost * gbp_rate,
    )

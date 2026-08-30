"""Currency conversion tool backed by the free open.er-api.com exchange rate API."""

import httpx
from langchain_core.tools import tool

from tools.net import system_certs_context, use_system_certs

_API_BASE = "https://open.er-api.com/v6/latest"


def _fetch_rates(base_currency: str) -> dict[str, float]:
    verify = system_certs_context() if use_system_certs() else True
    url = f"{_API_BASE}/{base_currency}"
    with httpx.Client(verify=verify, timeout=10.0) as client:
        response = client.get(url)
    response.raise_for_status()
    data = response.json()
    if data.get("result") != "success":
        raise ValueError(data.get("error-type", "exchange rate API returned an error"))
    return data["rates"]


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount from one currency to another using live exchange rates.

    Use this for travel-budget questions like "convert 5000 PKR to AED" or
    "how much is 200 USD in EUR". Currency codes must be ISO 4217 (e.g. PKR,
    AED, USD, EUR, GBP). Fetches current rates from a free, no-API-key
    exchange rate service, so results reflect today's rate rather than a
    fixed conversion.
    """
    from_code = from_currency.strip().upper()
    to_code = to_currency.strip().upper()

    try:
        rates = _fetch_rates(from_code)
    except httpx.HTTPError as exc:
        return f"Error fetching exchange rates for {from_code}: {exc}"
    except ValueError as exc:
        return f"Error: {exc}"

    if to_code not in rates:
        return f"Error: unknown currency code '{to_code}'"

    rate = rates[to_code]
    converted = amount * rate
    return (
        f"{amount:g} {from_code} = {converted:.2f} {to_code} "
        f"(rate: 1 {from_code} = {rate:.6f} {to_code})"
    )

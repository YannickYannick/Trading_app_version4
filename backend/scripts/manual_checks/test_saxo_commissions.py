"""Test live : illustration des commissions Saxo pour 1 TTE:xpar."""
import os
import sys

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config_django.settings.development")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.trading.models import AllAssets, BrokerAccount
from apps.trading.services.saxo import SaxoCostService
from apps.trading.services.saxo.payloads import build_order_payload

User = get_user_model()


def main():
    user = User.objects.order_by("id").first()
    account = BrokerAccount.objects.filter(user=user, is_active=True).filter(
        Q(broker_type__iexact="SAXO") | Q(broker__broker_type__iexact="SAXO")
    ).first()
    aa = AllAssets.objects.get(symbol="TTE:xpar", platform="SAXO")
    service = SaxoCostService.from_credentials(account.get_credentials_dict())
    keys = service.get_account_keys()
    print("keys_present", bool(keys.get("account_key")), bool(keys.get("client_key")))

    estimate = service.estimate_instrument_cost(
        uic=aa.saxo_uic,
        asset_type=aa.asset_type or "Stock",
        amount=1,
        holding_days=1,
    )
    print("INSTRUMENT", estimate.instrument, "UIC", estimate.uic, "CCY", estimate.account_currency)
    print("LONG_COMMISSION", estimate.long.trading.commissions)
    print("LONG_SPREAD", estimate.long.trading.spread)
    print("LONG_CONVERSION", estimate.long.trading.conversion_cost)
    print("LONG_EXCHANGE_FEE", estimate.long.trading.exchange_fee)
    print("LONG_TAX", estimate.long.holding.tax)
    print("LONG_TOTAL", estimate.long.total_cost, estimate.long.total_cost_pct)
    print("SHORT_COMMISSION", estimate.short.trading.commissions)
    print("SHORT_TOTAL", estimate.short.total_cost)

    payload = build_order_payload(
        uic=aa.saxo_uic,
        asset_type=aa.asset_type or "Stock",
        side="buy",
        quantity=1,
        account_key=keys.get("account_key") or "",
        order_type="Market",
        include_costs_field_group=True,
    )
    precheck = service.precheck_order(payload)
    print("PRECHECK", precheck.result, "commission", precheck.commission, "error", precheck.error)
    print("RAW_COST_KEYS", list((estimate.raw.get("Cost") or {}).keys()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Affiche les valeurs exactes utilisées pour `pnl` / `pnl_percent` dans `PositionListSerializer`.

Exécution (SQLite en mémoire si tu n'as pas les creds Supabase) :

  PowerShell:
    $env:USE_SUPABASE="false"; cd backend; python manage.py test apps.trading.tests.test_position_list_pnl_debug -v 2

  bash:
    USE_SUPABASE=false cd backend && python manage.py test apps.trading.tests.test_position_list_pnl_debug -v 2
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.trading.api.serializers import PositionListSerializer
from apps.trading.models import AllAssets, Broker, Position, Trade


def _print_pnl_ledger(label: str, data: dict) -> None:
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    keys = (
        "all_asset_symbol",
        "side",
        "quantity",
        "entry_price",
        "current_price",
        "reconstructed_entry_price",
        "yahoo_current_price",
        "pnl_basis_price",
        "pnl_mark_price",
        "pnl",
        "pnl_percent",
    )
    for k in keys:
        print(f"  {k}: {data.get(k)}")
    E = data.get("pnl_basis_price")
    C = data.get("pnl_mark_price")
    pct = data.get("pnl_percent")
    side = (data.get("side") or "").upper()
    if E is not None and C is not None and E != 0:
        if side == "LONG":
            check = 100.0 * (float(C) - float(E)) / float(E)
        else:
            check = 100.0 * (float(E) - float(C)) / float(E)
        print(f"  --- verification: 100*(mark-basis)/basis (side) => {check:.6f}% (API: {pct})")


class PositionListPnlDebugPrintTests(TestCase):
    """Cas chiffré proche de +2,97 % (LONG) pour lisibilité des impressions."""

    def setUp(self):
        self.user = User.objects.create_user(username="pnl_debug", password="x")
        self.broker = Broker.objects.create(
            name="Dbg Broker",
            broker_type=Broker.BrokerType.OTHER,
            is_active=True,
        )
        # Symbole Yahoo factice : uniquement pour le chemin include_yahoo_price (mocké).
        self.all_asset = AllAssets.objects.create(
            symbol="VWRL",
            name="VWRL ETF",
            platform="OTHER",
            asset_type="ETF",
            market="XAMS",
            currency="EUR",
            symbole_yahoo="VWRL.TEST",
            is_tradable=True,
        )
        # E ≈ 149,36 et C ≈ 153,80 → ~2,974 %
        self.position = Position.objects.create(
            user=self.user,
            all_asset=self.all_asset,
            broker=self.broker,
            quantity=Decimal("10"),
            entry_price=Decimal("149.36"),
            current_price=Decimal("153.80"),
            side="LONG",
            is_open=True,
        )

    def test_print_pnl_values_using_current_price_as_mark(self):
        ser = PositionListSerializer(
            self.position,
            context={"include_yahoo_price": False},
        )
        data = dict(ser.data)
        _print_pnl_ledger("Mark = current_price (pas Yahoo)", data)

        self.assertAlmostEqual(float(data["pnl_basis_price"]), 149.36, places=2)
        self.assertAlmostEqual(float(data["pnl_mark_price"]), 153.80, places=2)
        self.assertIsNone(data["yahoo_current_price"])
        self.assertAlmostEqual(float(data["pnl_percent"]), 2.97374, places=2)

    @patch(
        "apps.trading.services.data_providers.yahoo_finance.YahooFinanceService.get_current_price"
    )
    def test_print_pnl_values_using_yahoo_as_mark(self, mock_get_price):
        mock_get_price.return_value = 153.80
        ser = PositionListSerializer(
            self.position,
            context={"include_yahoo_price": True},
        )
        data = dict(ser.data)
        _print_pnl_ledger("Mark = yahoo_current_price (mock 153.80)", data)

        self.assertAlmostEqual(float(data["pnl_mark_price"]), 153.80, places=2)
        self.assertAlmostEqual(float(data["yahoo_current_price"]), 153.80, places=2)


class PositionListPnlFifoVsSaxoEntryTests(TestCase):
    """
    Quand les trades en base expliquent toute la qty ouverte, le PnL liste doit
    utiliser ce PRU (ex. prix d'exécution 139.72) et non seulement AverageOpenPrice Saxo.
    """

    def test_pnl_basis_prefers_fifo_when_qty_matches(self):
        user = User.objects.create_user(username="fifo_user", password="x")
        broker = Broker.objects.create(
            name="Saxo",
            broker_type=Broker.BrokerType.SAXO,
            is_active=True,
        )
        asset = AllAssets.objects.create(
            symbol="VWRL",
            name="VWRL",
            platform="SAXO",
            asset_type="ETF",
            market="XAMS",
            currency="EUR",
            symbole_yahoo="Not_searched",
            is_tradable=True,
        )
        position = Position.objects.create(
            user=user,
            all_asset=asset,
            broker=broker,
            quantity=Decimal("2"),
            entry_price=Decimal("149.36"),
            current_price=Decimal("153.80"),
            side="LONG",
            is_open=True,
        )
        Trade.objects.create(
            user=user,
            all_asset=asset,
            broker=broker,
            trade_type=Trade.TradeType.BUY,
            quantity=Decimal("2"),
            price=Decimal("139.72"),
            executed_at=timezone.now(),
        )
        ser = PositionListSerializer(position, context={"include_yahoo_price": False})
        data = dict(ser.data)
        self.assertAlmostEqual(float(data["pnl_basis_price"]), 139.72, places=2)
        self.assertAlmostEqual(float(data["pnl_mark_price"]), 153.80, places=2)
        # (153.80 - 139.72) / 139.72 * 100
        self.assertAlmostEqual(float(data["pnl_percent"]), 100.0 * (153.80 - 139.72) / 139.72, places=3)

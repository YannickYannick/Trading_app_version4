"""Tests du service de coûts Saxo (parsing, pagination, precheck, refresh token)."""
import json
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.trading.models import AllAssets, Broker, Trade, TransactionCost
from apps.trading.services.saxo.client import SaxoHttpClient, SaxoAuthError
from apps.trading.services.saxo.costs import (
    InstrumentCostEstimate,
    SaxoCostService,
    SideCost,
    match_trade_for_cost,
)
from apps.trading.services.saxo.payloads import build_order_payload

FIXTURES = Path(__file__).resolve().parent.parent / 'fixtures' / 'saxo'


def load_fixture(name: str):
    with open(FIXTURES / name, encoding='utf-8') as handle:
        return json.load(handle)


class SaxoCostParsingTestCase(TestCase):
    def test_parse_long_short_commissions(self):
        payload = load_fixture('tradingconditions_cost.json')
        long_side = SideCost.from_api(payload['Cost']['Long'])
        short_side = SideCost.from_api(payload['Cost']['Short'])
        self.assertEqual(long_side.trading.commissions, Decimal('1.0'))
        self.assertEqual(long_side.trading.conversion_cost, Decimal('2.58'))
        self.assertEqual(long_side.holding.tax, Decimal('0.5'))
        self.assertEqual(long_side.total_cost, Decimal('3.61'))
        self.assertEqual(short_side.trading.commissions, Decimal('1.0'))
        self.assertEqual(short_side.buy_sell, 'Sell')

    def test_estimate_instrument_cost_uses_account_key(self):
        client = MagicMock()
        client.request.side_effect = [
            {'ClientKey': 'ck'},
            {'Data': [{'AccountKey': 'ak|1'}]},
            load_fixture('tradingconditions_cost.json'),
        ]
        service = SaxoCostService(client)
        estimate = service.estimate_instrument_cost(23255427, 'Stock', 1, price=56.2, holding_days=1)
        self.assertIsInstance(estimate, InstrumentCostEstimate)
        self.assertEqual(estimate.long.trading.commissions, Decimal('1.0'))
        cost_call = client.request.call_args_list[-1]
        self.assertIn('/cs/v1/tradingconditions/cost/', cost_call.args[1])
        self.assertIn('ak%7C1', cost_call.args[1])

    def test_precheck_ok(self):
        client = MagicMock()
        client.request.return_value = load_fixture('precheck_ok.json')
        service = SaxoCostService(client)
        result = service.precheck_order(build_order_payload(
            uic=211, asset_type='Stock', side='buy', quantity=10, account_key='ak',
        ))
        self.assertTrue(result.ok)
        self.assertEqual(result.commission, Decimal('1.0'))
        self.assertEqual(result.estimated_cash_currency, 'EUR')

    def test_precheck_error(self):
        client = MagicMock()
        client.request.return_value = load_fixture('precheck_error.json')
        service = SaxoCostService(client)
        result = service.precheck_order({'Uic': 211})
        self.assertTrue(result.is_error)
        self.assertEqual(result.result, 'Error')
        self.assertIn('Not enough cash', result.error)

    def test_fetch_executed_costs_pagination(self):
        client = MagicMock()
        client.request.side_effect = [
            {'ClientKey': 'ck'},
            {'Data': [{'AccountKey': 'ak'}]},
            load_fixture('reports_trades_page1.json'),
            load_fixture('reports_trades_page2.json'),
        ]
        service = SaxoCostService(client)
        rows = service.fetch_executed_costs(date(2026, 8, 1), date(2026, 8, 24))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].trade_id, '1001')
        self.assertEqual(rows[0].commission, Decimal('1.0'))
        self.assertEqual(rows[1].trade_id, '1002')
        self.assertEqual(rows[1].commission, Decimal('2.5'))
        self.assertEqual(client.request.call_count, 4)

    def test_build_order_payload_identical_fields(self):
        payload = build_order_payload(
            uic=211, asset_type='Stock', side='BUY', quantity=1,
            account_key='ak', order_type='MARKET',
        )
        self.assertEqual(payload['OrderType'], 'Market')
        self.assertEqual(payload['BuySell'], 'Buy')
        self.assertTrue(payload['ManualOrder'])
        self.assertEqual(payload['OrderDuration'], {'DurationType': 'DayOrder'})


class SaxoHttpClientRefreshTestCase(TestCase):
    def test_refresh_on_401_then_success(self):
        session = MagicMock()
        unauthorized = MagicMock(status_code=401, content=b'{}')
        unauthorized.json.return_value = {'error': 'expired'}
        ok = MagicMock(status_code=200, content=b'{"ok": true}')
        ok.json.return_value = {'ok': True}
        session.request.side_effect = [unauthorized, ok]
        token_response = MagicMock()
        token_response.json.return_value = {
            'access_token': 'new-token',
            'refresh_token': 'new-refresh',
        }
        token_response.raise_for_status.return_value = None
        session.post.return_value = token_response

        client = SaxoHttpClient(
            {
                'environment': 'simulation',
                'access_token': 'old',
                'refresh_token': 'refresh',
                'client_id': 'id',
                'client_secret': 'secret',
            },
            session=session,
        )
        data = client.request('GET', '/port/v1/clients/me')
        self.assertEqual(data, {'ok': True})
        self.assertEqual(client.access_token, 'new-token')
        self.assertEqual(session.post.call_count, 1)

    def test_refresh_failure_raises(self):
        session = MagicMock()
        unauthorized = MagicMock(status_code=401, content=b'{}')
        unauthorized.json.return_value = {}
        session.request.return_value = unauthorized
        session.post.side_effect = Exception('boom')
        client = SaxoHttpClient(
            {
                'environment': 'simulation',
                'access_token': 'old',
                'refresh_token': 'refresh',
                'client_id': 'id',
            },
            session=session,
        )
        with self.assertRaises(SaxoAuthError):
            client.request('GET', '/port/v1/clients/me')


class SaxoCostMatchingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('costuser', 'c@test.com', 'pass')
        self.broker = Broker.objects.create(name='Saxo Bank', broker_type=Broker.BrokerType.SAXO)
        self.asset = AllAssets.objects.create(
            symbol='TTE:xpar',
            name='TotalEnergies SE',
            platform='SAXO',
            asset_type='Stock',
            market='FR',
            currency='EUR',
            saxo_uic=23255427,
        )
        self.trade = Trade.objects.create(
            user=self.user,
            all_asset=self.asset,
            broker=self.broker,
            trade_type='BUY',
            quantity=Decimal('1'),
            price=Decimal('56.2'),
            fees=Decimal('0'),
            executed_at=timezone.make_aware(datetime(2026, 8, 24, 14, 36), dt_timezone.utc),
            broker_trade_id='1001_5436680721',
        )

    def test_match_by_trade_id_contained(self):
        from apps.trading.services.saxo.costs import ExecutedTradeCost
        row = ExecutedTradeCost(
            trade_id='1001',
            uic=23255427,
            asset_type='Stock',
            amount=Decimal('1'),
            buy_sell='Buy',
            trade_date=datetime(2026, 8, 24, 14, 36, tzinfo=dt_timezone.utc),
            commission=Decimal('1'),
            exchange_fee=Decimal('0'),
            spread_cost=Decimal('0'),
            financing_cost=Decimal('0'),
            tax=Decimal('0'),
            total_cost=Decimal('1'),
            currency='EUR',
        )
        matched = match_trade_for_cost(self.user, row)
        self.assertEqual(matched.id, self.trade.id)

    def test_persist_updates_trade_fees_idempotent(self):
        from apps.trading.services.saxo.costs import ExecutedTradeCost
        row = ExecutedTradeCost(
            trade_id='1001',
            uic=23255427,
            asset_type='Stock',
            amount=Decimal('1'),
            buy_sell='Buy',
            trade_date=datetime(2026, 8, 24, 14, 36, tzinfo=dt_timezone.utc),
            commission=Decimal('1'),
            exchange_fee=Decimal('0'),
            spread_cost=Decimal('0'),
            financing_cost=Decimal('0'),
            tax=Decimal('0'),
            total_cost=Decimal('1'),
            currency='EUR',
            raw={'TradeId': '1001'},
        )
        service = SaxoCostService(MagicMock())
        first = service.persist_executed_costs(self.user, [row])
        second = service.persist_executed_costs(self.user, [row])
        self.assertEqual(first['created'], 1)
        self.assertEqual(second['created'], 0)
        self.assertEqual(second['updated'], 1)
        self.trade.refresh_from_db()
        self.assertEqual(self.trade.fees, Decimal('1'))
        self.assertEqual(TransactionCost.objects.filter(source='report').count(), 1)

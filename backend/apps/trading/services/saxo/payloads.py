"""Construction unique du payload d'ordre Saxo (precheck + placement)."""
from typing import Any, Dict, Optional


SAXO_ORDER_TYPE_MAP = {
    'MARKET': 'Market',
    'LIMIT': 'Limit',
    'STOP': 'Stop',
    'STOP_LIMIT': 'StopLimit',
    'market': 'Market',
    'limit': 'Limit',
    'stop': 'Stop',
    'stoplimit': 'StopLimit',
    'StopLimit': 'StopLimit',
}


def normalize_saxo_order_type(order_type: Optional[str], price=None) -> str:
    if not order_type:
        return 'Limit' if price else 'Market'
    mapped = SAXO_ORDER_TYPE_MAP.get(order_type, SAXO_ORDER_TYPE_MAP.get(str(order_type).upper()))
    return mapped or order_type


def build_order_payload(
    *,
    uic: int,
    asset_type: str,
    side: str,
    quantity: float,
    account_key: str,
    order_type: str = 'Market',
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    duration: str = 'DayOrder',
    manual_order: bool = True,
    include_costs_field_group: bool = False,
) -> Dict[str, Any]:
    """Payload identique pour /trade/v2/orders et /trade/v2/orders/precheck."""
    saxo_order_type = normalize_saxo_order_type(order_type, price)
    payload: Dict[str, Any] = {
        'Uic': int(uic),
        'AssetType': asset_type,
        'Amount': float(quantity),
        'BuySell': 'Buy' if str(side).lower() in ('buy', 'long') else 'Sell',
        'OrderType': saxo_order_type,
        'AccountKey': account_key,
        'OrderDuration': {'DurationType': duration},
        'ManualOrder': bool(manual_order),
    }
    if price is not None and saxo_order_type in ('Limit', 'StopLimit'):
        payload['OrderPrice'] = float(price)
    if stop_price is not None and saxo_order_type in ('Stop', 'StopLimit'):
        payload['StopPrice'] = float(stop_price)
    if include_costs_field_group:
        payload['FieldGroups'] = ['Costs']
    return payload

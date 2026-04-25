"""
Diagnostic simple de connectivité Binance depuis Railway.

Objectif:
- Vérifier si l'IP/region d'egress du serveur est bloquée par Binance (HTTP 451).
- Ne nécessite aucune clé API (endpoints publics).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def fetch_json(url: str, timeout_s: int = 10) -> tuple[int, dict | str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TradingApp/1.0 (+Railway diagnostic)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return status, json.loads(raw)
            except json.JSONDecodeError:
                return status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


def main() -> int:
    tests = [
        ("server time", "https://api.binance.com/api/v3/time"),
        ("exchangeInfo (BTCUSDT)", "https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT"),
        ("ticker price (BTCUSDT)", "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"),
    ]

    print("== Binance connectivity diagnostic ==")
    ok_any = False
    for name, url in tests:
        status, data = fetch_json(url)
        ok_any = ok_any or (200 <= status < 300)
        print(f"\n-- {name} --")
        print(f"GET {url}")
        print(f"status={status}")
        if isinstance(data, dict):
            # Affiche un subset compact
            print("json=", json.dumps(data, ensure_ascii=False)[:500])
        else:
            print("body=", str(data)[:500])

    if not ok_any:
        print("\nResult: ❌ Aucun endpoint public Binance n'a répondu en 2xx.")
        print("Si tu vois du 451, c'est un blocage Binance 'restricted location' (souvent IP cloud/datacenter).")
        return 2

    print("\nResult: ✅ Au moins un endpoint public Binance répond correctement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


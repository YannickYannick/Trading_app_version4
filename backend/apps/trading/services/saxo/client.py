"""Client HTTP Saxo : token Bearer, retry 429/5xx, refresh sur 401."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger('trading_app.saxo')

LIVE_BASE_URL = 'https://gateway.saxobank.com/openapi'
SIM_BASE_URL = 'https://gateway.saxobank.com/sim/openapi'
LIVE_AUTH_URL = 'https://live.logonvalidation.net'
SIM_AUTH_URL = 'https://sim.logonvalidation.net'


class SaxoHttpError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class SaxoAuthError(SaxoHttpError):
    pass


class SaxoHttpClient:
    """Session unique pour les appels OpenAPI Saxo."""

    def __init__(
        self,
        credentials: Dict[str, Any],
        session: Optional[requests.Session] = None,
        timeout: int = 30,
        max_retries: int = 4,
    ):
        self.credentials = credentials
        environment = (credentials.get('environment') or 'live').lower()
        if environment == 'live':
            self.base_url = LIVE_BASE_URL
            self.auth_url = LIVE_AUTH_URL
        else:
            self.base_url = SIM_BASE_URL
            self.auth_url = SIM_AUTH_URL
        self.access_token = credentials.get('access_token')
        self.refresh_token = credentials.get('refresh_token')
        self.client_id = credentials.get('client_id')
        self.client_secret = credentials.get('client_secret')
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = session or requests.Session()

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        raw: bool = False,
    ) -> Any:
        last_error: Optional[Exception] = None
        refreshed = False

        for attempt in range(self.max_retries + 1):
            try:
                response = self._send(method, endpoint, params=params, json_data=json_data)
            except requests.RequestException as exc:
                last_error = SaxoHttpError(f'Request failed: {exc}')
                self._backoff(attempt)
                continue

            if response.status_code == 401 and not refreshed:
                if not self.refresh_access_token():
                    raise SaxoAuthError('Token refresh failed', status_code=401)
                refreshed = True
                continue

            if response.status_code in (429,) or response.status_code >= 500:
                last_error = SaxoHttpError(
                    f'Saxo HTTP {response.status_code}',
                    status_code=response.status_code,
                    body=self._safe_body(response),
                )
                logger.warning('Saxo retryable error %s on %s %s', response.status_code, method, endpoint)
                self._backoff(attempt)
                continue

            if response.status_code >= 400:
                body = self._safe_body(response)
                raise SaxoHttpError(
                    f'API request failed: {response.status_code} - {body}',
                    status_code=response.status_code,
                    body=body,
                )

            if raw:
                return response
            if not response.content:
                return {}
            return response.json()

        raise last_error or SaxoHttpError('Saxo request failed after retries')

    def refresh_access_token(self) -> bool:
        if not self.refresh_token or not self.client_id:
            return False
        try:
            response = self._session.post(
                f'{self.auth_url}/token',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret or '',
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token', self.refresh_token)
            self.credentials['access_token'] = self.access_token
            self.credentials['refresh_token'] = self.refresh_token
            logger.info('Saxo HTTP client: token refreshed')
            return bool(self.access_token)
        except Exception as exc:
            logger.error('Saxo HTTP client token refresh failed: %s', exc)
            return False

    def _send(self, method: str, endpoint: str, params=None, json_data=None) -> requests.Response:
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            url = endpoint
        else:
            url = urljoin(self.base_url.rstrip('/') + '/', endpoint.lstrip('/'))
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
        }
        if json_data is not None:
            headers['Content-Type'] = 'application/json'
        return self._session.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
            timeout=self.timeout,
        )

    @staticmethod
    def _backoff(attempt: int) -> None:
        time.sleep(min(8.0, 0.5 * (2 ** attempt)))

    @staticmethod
    def _safe_body(response: requests.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return response.text

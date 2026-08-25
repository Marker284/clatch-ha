"""Async-клиент для приватного API Clatch (clatch3.mts.ru)."""
from __future__ import annotations

from typing import Any

import aiohttp

from .const import API_BASE_URL


class ClatchApiError(Exception):
    """Общая ошибка обращения к Clatch API."""


class ClatchAuthError(ClatchApiError):
    """Токен недействителен или истёк."""


class ClatchApiClient:
    def __init__(self, session: aiohttp.ClientSession, token: str, profile_id: str) -> None:
        self._session = session
        self._token = token
        self._profile_id = profile_id

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    async def _get(self, path: str) -> Any:
        url = f"{API_BASE_URL}{path}"
        try:
            async with self._session.get(
                url, headers=self._headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status in (401, 403):
                    raise ClatchAuthError(f"Clatch API вернул {resp.status} — токен недействителен")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise ClatchApiError(str(err)) from err

    async def async_get_period_dates(self) -> list[str]:
        data = await self._get(f"/api/v1/period/{self._profile_id}")
        return data.get("data", [])

    async def async_get_symptoms(self) -> list[dict]:
        data = await self._get(f"/api/v1/symptoms/{self._profile_id}")
        return data.get("data", [])

    async def async_validate(self) -> None:
        """Проверить токен + profile_id одним лёгким запросом."""
        await self.async_get_period_dates()

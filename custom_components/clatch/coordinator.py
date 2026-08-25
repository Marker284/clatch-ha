"""DataUpdateCoordinator: считает статус цикла из сырых дат месячных Clatch."""
from __future__ import annotations

import datetime as dt
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ClatchApiClient, ClatchApiError, ClatchAuthError
from .const import DOMAIN, PHASES

_LOGGER = logging.getLogger(__name__)


def _episodes(dates: list[dt.date]) -> list[list[dt.date]]:
    dates = sorted(dates)
    episodes = [[dates[0]]]
    for d in dates[1:]:
        if (d - episodes[-1][-1]).days <= 1:
            episodes[-1].append(d)
        else:
            episodes.append([d])
    return episodes


def _get_phase(cycle_day: int, cycle_length: int) -> dict:
    frac = cycle_day / cycle_length
    frac = max(0.0, min(0.999, frac))
    for phase in PHASES:
        lo, hi = phase["range"]
        if lo <= frac < hi:
            return phase
    return PHASES[-1]


def _compute_status(raw_dates: list[str], symptoms: list[dict]) -> dict:
    dates = sorted(dt.date.fromisoformat(d[:10]) for d in raw_dates)
    if not dates:
        raise UpdateFailed("Clatch API не вернул ни одной даты месячных")

    episodes = _episodes(dates)
    starts = [ep[0] for ep in episodes]
    episode_lengths = [len(ep) for ep in episodes]

    cycle_lengths = [(starts[i + 1] - starts[i]).days for i in range(len(starts) - 1)]
    recent_cycle = cycle_lengths[-6:] if len(cycle_lengths) >= 6 else cycle_lengths
    recent_period = episode_lengths[-6:] if len(episode_lengths) >= 6 else episode_lengths

    avg_cycle = round(sum(recent_cycle) / len(recent_cycle)) if recent_cycle else 28
    avg_period = round(sum(recent_period) / len(recent_period)) if recent_period else 5

    last_start = starts[-1]
    today = dt.date.today()
    cycle_day = (today - last_start).days + 1
    is_period_now = today in dates

    next_period_start = last_start + dt.timedelta(days=avg_cycle)
    period_end_est = last_start + dt.timedelta(days=avg_period - 1)
    ovulation_date = last_start + dt.timedelta(days=round(avg_cycle * 0.5))

    phase = _get_phase(cycle_day, avg_cycle)

    last_diary_entry = None
    if symptoms:
        last_diary_entry = sorted(symptoms, key=lambda x: x["date"], reverse=True)[0]

    return {
        "today": today,
        "cycle_day": cycle_day,
        "cycle_length": avg_cycle,
        "avg_period_length": avg_period,
        "is_period_now": is_period_now,
        "last_period_start": last_start,
        "next_period_start": next_period_start,
        "days_until_period": (next_period_start - today).days,
        "days_until_period_end": (period_end_est - today).days,
        "ovulation_date": ovulation_date,
        "days_until_ovulation": (ovulation_date - today).days,
        "cycle_lengths_recent": recent_cycle,
        "phase_key": phase["key"],
        "phase_title": phase["title"],
        "phase_note": phase["note"],
        "last_diary_entry": last_diary_entry,
    }


class ClatchDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: ClatchApiClient,
        update_interval: dt.timedelta,
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> dict:
        try:
            raw_dates = await self.client.async_get_period_dates()
            symptoms = await self.client.async_get_symptoms()
        except ClatchAuthError as err:
            raise UpdateFailed(f"Токен недействителен: {err}") from err
        except ClatchApiError as err:
            raise UpdateFailed(f"Ошибка Clatch API: {err}") from err

        return _compute_status(raw_dates, symptoms)

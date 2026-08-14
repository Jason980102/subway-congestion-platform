"""Import and match current NYC-permitted events for NYU-area stations."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select

from database import SessionLocal
from models import Event, Prediction, Station


API_ENDPOINT = "https://data.cityofnewyork.us/resource/tvpp-9vvx.json"

def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def classify_event_risk(event_type: str, closure: str) -> str:
    combined = f"{event_type} {closure}".upper()
    high_terms = ("PARADE", "FESTIVAL", "FULL STREET", "FULL CLOSURE", "MARATHON")
    medium_terms = (
        "SPECIAL EVENT", "FAIR", "RALLY", "CONCERT", "FARMERS MARKET",
        "PARTIAL", "SIDEWALK", "SPORT",
    )
    if any(term in combined for term in high_terms):
        return "High"
    if any(term in combined for term in medium_terms):
        return "Medium"
    return "Low"


def map_location_to_station(location: str, stations: list[Station]) -> int | None:
    normalized = (location or "").upper()
    compact = " ".join(normalized.replace(",", " ").split())
    complex_id: int | None = None

    if "WASHINGTON SQUARE" in compact or "WEST 4 STREET" in compact or "W 4 STREET" in compact:
        complex_id = 167
    elif "ASTOR PLACE" in compact or "COOPER SQUARE" in compact:
        complex_id = 407
    elif re.search(r"(?<!\d)(?:WEST|W)?\s*8(?:TH)? STREET", compact):
        complex_id = 16
    elif (
        "BROADWAY LAFAYETTE" in compact
        or "BROADWAY-LAFAYETTE" in compact
        or ("LAFAYETTE" in compact and "HOUSTON" in compact)
        or ("BLEECKER" in compact and ("BROADWAY" in compact or "LAFAYETTE" in compact or "BOWERY" in compact))
    ):
        complex_id = 619

    if complex_id is None:
        return None
    for station in stations:
        if station.mta_complex_id == complex_id:
            return station.station_id
    return None


def fetch_current_events(days_ahead: int = 180) -> list[dict]:
    now = datetime.now()
    end = now + timedelta(days=days_ahead)
    where = (
        "event_borough='Manhattan' "
        f"AND end_date_time >= '{now:%Y-%m-%dT%H:%M:%S}' "
        f"AND start_date_time < '{end:%Y-%m-%dT%H:%M:%S}'"
    )
    params = urlencode({"$where": where, "$limit": 50000, "$order": "start_date_time"})
    request = Request(f"{API_ENDPOINT}?{params}", headers={"Accept": "application/json"})
    token = os.getenv("NYC_OPEN_DATA_APP_TOKEN")
    if token:
        request.add_header("X-App-Token", token)
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def sync_official_events(days_ahead: int = 180) -> dict[str, int]:
    rows = fetch_current_events(days_ahead)
    inserted = updated = mapped = skipped_unmapped = stale_removed = 0

    with SessionLocal.begin() as session:
        stations = list(session.scalars(select(Station)).all())
        existing = {
            event.source_event_id: event
            for event in session.scalars(
                select(Event).where(Event.source_event_id.is_not(None))
            ).all()
        }

        mapped_rows: dict[str, tuple[dict, int]] = {}
        for row in rows:
            official_id = str(row.get("event_id", "")).strip()
            location = str(row.get("event_location", "")).strip()
            station_id = map_location_to_station(location, stations)
            if not official_id or station_id is None:
                skipped_unmapped += 1
                continue

            # Socrata may return multiple road segments for one permit. Keep one
            # record per official event and mapped station, rather than creating
            # duplicate EVENT rows for the same user-facing alert.
            source_id = f"{official_id}:{station_id}"
            mapped_rows.setdefault(source_id, (row, station_id))

        for source_id, (row, station_id) in mapped_rows.items():
            location = str(row.get("event_location", "")).strip()

            event_type = str(row.get("event_type", "")).strip()
            closure = str(row.get("street_closure_type", "")).strip()
            values = {
                "station_id": station_id,
                "event_name": str(row.get("event_name") or "Permitted event")[:200],
                "event_type": event_type[:100] or None,
                "location": location[:200] or None,
                "start_time": parse_timestamp(row["start_date_time"]),
                "end_time": parse_timestamp(row["end_date_time"]),
                "source_event_id": source_id,
                "event_agency": str(row.get("event_agency", ""))[:150] or None,
                "street_closure_type": closure[:100] or None,
                "risk_level": classify_event_risk(event_type, closure),
            }
            event = existing.get(source_id)
            if event is None:
                session.add(Event(**values))
                inserted += 1
            else:
                for key, value in values.items():
                    setattr(event, key, value)
                updated += 1
            mapped += 1

        desired_source_ids = set(mapped_rows)
        stale_events = list(
            session.scalars(
                select(Event).where(
                    Event.source_event_id.is_not(None),
                    Event.source_event_id.not_in(desired_source_ids),
                    ~select(Prediction.prediction_id)
                    .where(Prediction.event_id == Event.event_id)
                    .exists(),
                )
            ).all()
        )
        for event in stale_events:
            session.delete(event)
            stale_removed += 1

    return {
        "official_rows_downloaded": len(rows),
        "nyu_area_events_mapped": mapped,
        "events_inserted": inserted,
        "events_updated": updated,
        "stale_unreferenced_events_removed": stale_removed,
        "events_outside_mapping": skipped_unmapped,
    }


def find_nearby_event(session, station_id: int, when: datetime) -> Event | None:
    window_start = when - timedelta(hours=2)
    window_end = when + timedelta(hours=2)
    candidates = list(
        session.scalars(
            select(Event).where(
                Event.station_id == station_id,
                Event.source_event_id.is_not(None),
                Event.start_time <= window_end,
                Event.end_time >= window_start,
            )
        ).all()
    )
    rank = {"High": 3, "Medium": 2, "Low": 1, None: 0}
    return max(candidates, key=lambda event: rank[event.risk_level], default=None)

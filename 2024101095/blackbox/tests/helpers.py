from __future__ import annotations

from datetime import datetime
from typing import Any


def get_field(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
    return default


def extract_list(payload: Any, *keys: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value

    for value in payload.values():
        if isinstance(value, list):
            return value

    return []


def extract_object(payload: Any, *keys: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, dict):
                return value
    return payload if isinstance(payload, dict) else {}


def extract_cart_item(cart_payload: Any, product_id: int) -> dict[str, Any] | None:
    items = extract_list(cart_payload, "items", "cart_items")
    for item in items:
        item_product_id = get_field(item, "product_id", "id")
        if item_product_id is None:
            product = get_field(item, "product", default={})
            item_product_id = get_field(product, "product_id", "id")
        if item_product_id == product_id:
            return item
    return None


def parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None

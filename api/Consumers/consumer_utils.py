import json
from .consumer_constants import MessageType


def create_websocket_payload(**kwargs) -> str:
    """Create a standardized WebSocket payload."""
    return json.dumps({
        "type": MessageType.MESSAGE,
        "is_successfully": "true",
        **kwargs
    })


def safe_nested_get(data: dict, *keys, default=None):
    """Safely get nested dictionary values."""
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError, IndexError):
        return default

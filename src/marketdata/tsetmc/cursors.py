import base64
from typing import Any


def cursor(epoch: Any, position: int) -> str:
    return base64.urlsafe_b64encode(f"tsetmc1:{epoch}:{position}".encode()).decode()


def position(token: str, epoch: Any) -> int:
    try:
        prefix, namespace, number = (
            base64.b64decode(token, altchars=b"-_", validate=True).decode().split(":")
        )
        if prefix != "tsetmc1" or namespace != str(epoch) or not number.isdigit():
            raise ValueError()
        return int(number)
    except (ValueError, UnicodeError):
        raise ValueError("resync_required") from None

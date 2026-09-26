from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Endpoint:
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str


DATABASE = Endpoint(
    "GET",
    "/api/codex/app/database/",
)

LIVE = Endpoint(
    "GET",
    "/api/codex/app/live/",
)

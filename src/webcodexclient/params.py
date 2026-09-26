from typing import TypedDict


class DataParams(TypedDict, total=False):
    lang: str
    category: str
    entry: str
    t: int  # Tier
    q: str  # Query
    c: str  # Item type
    cl: int  # Useable by
    f: str  # Family

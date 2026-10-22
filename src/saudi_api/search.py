"""The one builder of catalogue search conditions and scores (ADR-003).

A row matches a query when its `search_vector` matches the English, Arabic or simple
tsquery, or when the folded query is word-similar to its `search_text` (pg_trgm `<%`,
threshold `pg_trgm.word_similarity_threshold`, default 0.6). GIN indexes serve both
conditions. `fold` mirrors the SQL `catalog_fold` for code outside SQL.
"""

from __future__ import annotations

import re

from sqlalchemy import ColumnElement, Float, cast, func, literal_column, or_, type_coerce
from sqlalchemy.dialects.postgresql import TSQUERY
from sqlalchemy.orm import InstrumentedAttribute

# A longer query is cut: the longest catalogue name is under 200 characters, and the
# cost of websearch_to_tsquery grows with its input.
MAX_QUERY_LENGTH = 200

_DIACRITICS = re.compile("[ً-ٰٟـ]")
_FOLD_TABLE = str.maketrans("أإآٱةى", "ااااهي")
_CONFIGS = ("english", "arabic", "simple")


def fold(value: str) -> str:
    """The same folding as the SQL function `catalog_fold`."""
    return _DIACRITICS.sub("", value.lower()).translate(_FOLD_TABLE)


def normalize_query(value: str | None) -> str | None:
    """Collapse whitespace and cut to MAX_QUERY_LENGTH; an empty query is no query."""
    if value is None:
        return None
    collapsed = " ".join(value.split())[:MAX_QUERY_LENGTH]
    return collapsed or None


def tsquery(query: str) -> ColumnElement[str]:
    """The English, Arabic and simple readings of a query, combined with OR."""
    readings = [
        func.websearch_to_tsquery(literal_column(f"'{config}'::regconfig"), query)
        for config in _CONFIGS
    ]
    combined = readings[0].op("||")(readings[1]).op("||")(readings[2])
    return type_coerce(combined, TSQUERY)


def match(
    vector: InstrumentedAttribute[str], text: InstrumentedAttribute[str], query: str
) -> ColumnElement[bool]:
    return or_(
        vector.op("@@")(tsquery(query)),
        func.catalog_fold(query).op("<%")(text),
    )


def score(
    vector: InstrumentedAttribute[str], text: InstrumentedAttribute[str], query: str
) -> ColumnElement[float]:
    rank = cast(func.ts_rank_cd(vector, tsquery(query)), Float)
    similarity = cast(func.word_similarity(func.catalog_fold(query), text), Float)
    return type_coerce(rank + similarity, Float)

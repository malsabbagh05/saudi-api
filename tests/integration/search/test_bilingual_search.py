"""Bilingual search (ADR-003) on the real server and the repository's catalogue.

The evaluation queries below are the fixed set a ranking change is measured against
(pr-readiness rule 15): each names the entry that must rank first.
"""

import json

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from saudi_api import queries, search
from saudi_api.models import ApiRow
from tests.support.catalog import REPOSITORY_CATALOG, sync
from tests.support.postgres import postgres_engine

EVALUATION = [
    ("العنوان الوطني", {"spl-national-address", "wathq-national-address"}),
    ("الفوترة الإلكترونية", {"zatca-e-invoicing"}),
    ("السجل التجاري", {"wathq-commercial-registration"}),
    ("البيانات المفتوحة", {"rcrc-open-data", "datasaudi"}),
    ("مترو", {"rcrc-open-data"}),
    ("الاحصاء", {"datasaudi"}),
    ("national address", {"spl-national-address", "wathq-national-address"}),
    ("e-invoicing", {"zatca-e-invoicing"}),
    ("open banking", {"alrajhi-open-banking", "sama-open-banking", "lean-open-banking"}),
    ("buy now pay later", {"tamara-payments", "tabby-payments"}),
    ("sms", {"taqnyat-messaging"}),
]


@pytest.fixture(scope="module")
def sessions():
    engine = postgres_engine("search")
    sync(engine, REPOSITORY_CATALOG)
    try:
        yield sessionmaker(engine)
    finally:
        engine.dispose()


@pytest.mark.parametrize(("query", "expected"), EVALUATION)
def test_evaluation_queries_rank_the_expected_entry_first(sessions, query, expected):
    with sessions() as db:
        page = queries.list_apis(db, q=query, limit=5)
    assert page.items, f"no result for {query!r}"
    assert page.items[0].slug in expected


def test_arabic_letter_variants_and_diacritics_fold_together(sessions):
    with sessions() as db:
        plain = [a.slug for a in queries.list_apis(db, q="الاحصاء").items]
        hamza = [a.slug for a in queries.list_apis(db, q="الإحصاء").items]
        voweled = [a.slug for a in queries.list_apis(db, q="الإِحْصَاء").items]
    assert plain == hamza == voweled
    assert search.fold("الإِحْصَاءُ مدرسة") == "الاحصاء مدرسه"


def test_search_conditions_can_use_their_gin_indexes(sessions):
    statement = select(ApiRow.slug).where(
        search.match(ApiRow.search_vector, ApiRow.search_text, "العنوان الوطني")
    )
    compiled = statement.compile(sessions.kw["bind"])
    with sessions() as db:
        # The table is small, so force the planner off the sequential scan to prove the
        # indexes can serve the statement as the code sends it (docs/development/database.md).
        db.execute(text("SET LOCAL enable_seqscan = off"))
        connection = db.connection()
        plan = connection.exec_driver_sql(
            f"EXPLAIN (FORMAT JSON) {compiled}", compiled.params
        ).scalar_one()
    rendered = json.dumps(plan)
    assert "apis_search_vector" in rendered
    assert "apis_search_text" in rendered
    assert "Seq Scan" not in rendered


def test_unknown_words_return_nothing(sessions):
    with sessions() as db:
        assert queries.list_apis(db, q="zzqqxxyy").total == 0

"""The catalogue files: the repository's own entries and the rules that guard them."""

import pytest

from saudi_api.catalog.loader import CatalogError, load_catalog
from saudi_api.cli import main
from tests.support.catalog import REPOSITORY_CATALOG, api_entry, new_catalog, write_api


def test_the_repository_catalogue_is_valid():
    catalog = load_catalog(REPOSITORY_CATALOG)
    assert catalog.apis and catalog.providers and catalog.sectors
    assert all(api.name.ar and api.name.en for api in catalog.apis)


def test_catalog_check_reports_every_problem_and_fails(tmp_path, capsys):
    directory = new_catalog(tmp_path)
    write_api(directory, api_entry("good"))
    write_api(directory, api_entry("no-arabic", name={"en": "Only English", "ar": "Only English"}))
    write_api(directory, api_entry("ghost-provider", provider="missing"))

    assert main(["catalog", "check", "--dir", str(directory)]) == 1
    errors = capsys.readouterr().err
    assert "apis/no-arabic.yaml: name.ar" in errors or "apis/no-arabic.yaml: name" in errors
    assert "unknown provider 'missing'" in errors
    assert "catalogue invalid: 2 problem(s)" in errors


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"access": {"level": "registration", "auth": ["api_key"], "pricing": "paid"}},
            "api_key location is required",
        ),
        (
            {"access": {"level": "registration", "auth": ["none"], "pricing": "free"}},
            "an API with auth `none` has access level `open`",
        ),
        (
            {"access": {"level": "open", "auth": ["none", "api_key"], "pricing": "free"}},
            "auth `none` stands alone",
        ),
        ({"documentation_url": "http://provider.example/docs"}, "must be an https:// URL"),
    ],
)
def test_access_and_url_rules(tmp_path, overrides, message):
    directory = new_catalog(tmp_path)
    write_api(directory, api_entry("rules", **overrides))
    with pytest.raises(CatalogError) as error:
        load_catalog(directory)
    assert any(message in problem for problem in error.value.problems)


def test_agent_invocation_needs_keyless_get_endpoints_a_budget_and_evidence(tmp_path):
    directory = new_catalog(tmp_path)
    endpoint = {
        "id": "items",
        "method": "POST",
        "path": "/items",
        "summary": {"en": "Items.", "ar": "العناصر."},
    }
    write_api(
        directory,
        api_entry(
            "invocable",
            base_urls=[{"url": "https://api.provider.example"}],
            endpoints=[endpoint],
            usage={"agent_invocation": "allowed"},
        ),
    )
    with pytest.raises(CatalogError) as error:
        load_catalog(directory)
    assert any("agent invocation needs GET endpoints only" in p for p in error.value.problems)


def test_path_parameters_must_be_declared(tmp_path):
    directory = new_catalog(tmp_path)
    endpoint = {
        "id": "item",
        "method": "GET",
        "path": "/items/{id}",
        "summary": {"en": "One item.", "ar": "عنصر واحد."},
    }
    write_api(
        directory,
        api_entry(
            "paths", base_urls=[{"url": "https://api.provider.example"}], endpoints=[endpoint]
        ),
    )
    with pytest.raises(CatalogError) as error:
        load_catalog(directory)
    assert any("path parameters ['id'] differ from declared []" in p for p in error.value.problems)

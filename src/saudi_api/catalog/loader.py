"""Read and validate the catalogue directory as one unit (ADR-002).

`load_catalog` is the only reader of the YAML files. It parses each file through the
schema, checks the references between files, and computes the content digest that the
database projection records.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from saudi_api.catalog.schema import Api, Provider, Sector, SectorsFile, entry_context


@dataclass(frozen=True)
class Catalog:
    sectors: tuple[Sector, ...]
    providers: tuple[Provider, ...]
    apis: tuple[Api, ...]
    digest: str


class CatalogError(Exception):
    """The catalogue directory is invalid; `problems` lists every finding."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__(f"{len(problems)} catalogue problem(s)")
        self.problems = problems


def catalog_digest(directory: Path) -> str:
    """A digest of every YAML file's relative path and bytes."""
    digest = sha256()
    for path in sorted(directory.rglob("*.yaml")):
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_catalog(directory: Path, *, allow_loopback_http: bool = False) -> Catalog:
    """Parse and check the whole directory; `allow_loopback_http` is the development and
    test opt-out of ADR-004 and is never set by `catalog check`."""
    problems: list[str] = []
    context = entry_context(allow_loopback_http)
    if not directory.is_dir():
        raise CatalogError([f"{directory}: not a directory"])

    sectors_file = _parse(directory / "sectors.yaml", SectorsFile, problems, context)
    sectors = sectors_file.sectors if sectors_file else []
    providers = _parse_each(directory / "providers", Provider, problems, context)
    apis = _parse_each(directory / "apis", Api, problems, context)

    _unique([s.slug for s in sectors], "sector", problems)
    sector_slugs = {s.slug for s in sectors}
    provider_slugs = {p.slug for p in providers}
    for api in apis:
        if api.provider not in provider_slugs:
            problems.append(f"apis/{api.slug}.yaml: unknown provider {api.provider!r}")
        for sector in api.sectors:
            if sector not in sector_slugs:
                problems.append(f"apis/{api.slug}.yaml: unknown sector {sector!r}")
    used_providers = {api.provider for api in apis}
    for provider in providers:
        if provider.slug not in used_providers:
            problems.append(f"providers/{provider.slug}.yaml: no API names this provider")

    if problems:
        raise CatalogError(problems)
    return Catalog(
        sectors=tuple(sectors),
        providers=tuple(sorted(providers, key=lambda p: p.slug)),
        apis=tuple(sorted(apis, key=lambda a: a.slug)),
        digest=catalog_digest(directory),
    )


def _parse_each[M: Provider | Api](
    directory: Path, model: type[M], problems: list[str], context: dict[str, bool]
) -> list[M]:
    entries: list[M] = []
    if not directory.is_dir():
        problems.append(f"{directory.name}/: missing")
        return entries
    for path in sorted(directory.glob("*.yaml")):
        entry = _parse(path, model, problems, context)
        if entry is None:
            continue
        if entry.slug != path.stem:
            problems.append(f"{directory.name}/{path.name}: slug {entry.slug!r} differs")
            continue
        entries.append(entry)
    return entries


def _parse[M: BaseModel](
    path: Path, model: type[M], problems: list[str], context: dict[str, bool]
) -> M | None:
    label = f"{path.parent.name}/{path.name}" if path.parent.name != "catalog" else path.name
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"{label}: missing")
        return None
    except yaml.YAMLError as error:
        problems.append(f"{label}: invalid YAML ({error.__class__.__name__})")
        return None
    try:
        return model.model_validate(document, context=context)
    except ValidationError as error:
        for item in error.errors():
            location = ".".join(str(part) for part in item["loc"]) or "<root>"
            problems.append(f"{label}: {location}: {item['msg']}")
        return None


def _unique(values: list[str], kind: str, problems: list[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            problems.append(f"sectors.yaml: {kind} {value!r} repeats")
        seen.add(value)

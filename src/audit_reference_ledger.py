"""Check the standalone bibliography/provenance and 12+5+5 calibration ledgers."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "bibliography_manifest.csv"
RESOURCES = ROOT / "external_resources.csv"
CALIBRATION = ROOT / "literature-calibration.csv"
OUT = ROOT / "results" / "reference-ledger-audit.json"
DOI_RE = re.compile(r"^doi:10\.\d{4,9}/\S+$", re.I)
URL_RE = re.compile(r"^url:https://", re.I)


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run() -> dict:
    errors: list[str] = []
    manifest = load(MANIFEST)
    resources = load(RESOURCES)
    calibration = load(CALIBRATION)

    keys = [row["citation_key"] for row in manifest]
    identifiers = [row["persistent_identifier"] for row in manifest]
    if len(manifest) != 50:
        errors.append(f"expected current inventory of 50 bibliography rows, found {len(manifest)}")
    if len(keys) != len(set(keys)):
        errors.append("duplicate bibliography citation key")
    if len(identifiers) != len(set(identifiers)):
        errors.append("duplicate bibliography persistent identifier")
    for row in manifest:
        if not row["title"].strip() or not row["year"].isdigit() or not row["venue"].strip():
            errors.append(f"incomplete bibliography metadata for {row['citation_key']}")
        ident = row["persistent_identifier"].strip()
        if not (DOI_RE.match(ident) or URL_RE.match(ident)):
            errors.append(f"malformed persistent identifier for {row['citation_key']}: {ident}")

    mapped = [row for row in resources if row.get("citation_key", "").strip()]
    counts = Counter(row["citation_key"] for row in mapped)
    bad = {key: counts.get(key, 0) for key in keys if counts.get(key, 0) != 1}
    if bad:
        errors.append(f"citation-resource mapping not one-to-one: {bad}")
    extra = sorted(set(counts) - set(keys))
    if extra:
        errors.append(f"resource citation keys absent from manifest: {extra}")

    by_key = {row["citation_key"]: row for row in mapped}
    for row in manifest:
        resource = by_key.get(row["citation_key"])
        if resource is None:
            continue
        ident = row["persistent_identifier"]
        url = resource["scholarly_or_official_url"].strip().lower().rstrip("/")
        if ident.startswith("doi:") and ident[4:].lower() not in url:
            errors.append(f"DOI mismatch for {row['citation_key']}")
        if ident.startswith("url:") and ident[4:].lower().rstrip("/") != url:
            errors.append(f"URL mismatch for {row['citation_key']}")
        for field in ("access_date", "acquisition_method_and_read_status", "supported_claim", "integration_mode"):
            if not resource[field].strip():
                errors.append(f"missing {field} for {row['citation_key']}")

    categories = Counter(row["category"] for row in calibration)
    expected = {"same-venue-full": 12, "influential-full": 5, "adjacent-full": 5}
    if categories != expected:
        errors.append(f"calibration categories {dict(categories)} != {expected}")
    titles = [row["source_title"].strip().casefold() for row in calibration]
    if len(calibration) != 22 or len(titles) != len(set(titles)):
        errors.append("calibration must contain 22 distinct titles")
    for row in calibration:
        for field in ("scholarly_url", "readable_full_text_url", "read_scope", "delta_to_this_paper"):
            if not row[field].strip():
                errors.append(f"calibration row {row['source_title']!r} missing {field}")

    report = {
        "all_reference_ledger_checks_passed": not errors,
        "bibliography_manifest_rows": len(manifest),
        "citation_resource_mappings": len(mapped),
        "persistent_identifiers_unique": len(set(identifiers)),
        "external_resource_rows": len(resources),
        "calibration_rows": len(calibration),
        "calibration_categories": dict(sorted(categories.items())),
        "errors": errors,
        "scope": "standalone local ledger consistency; remote publisher metadata was inspected separately and recorded in external_resources.csv",
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["all_reference_ledger_checks_passed"] else 1)

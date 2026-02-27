#!/usr/bin/env python3
"""
import_species_csv.py — Luthia Species Data Importer
====================================================
Reads a species CSV file (tonewood-species.csv)
and writes a structured, validated JSON file suitable for database seeding,
API consumption, or standalone reference use.

Usage
-----
    python import_species_csv.py                         # default paths
    python import_species_csv.py --input path/to/file.csv
    python import_species_csv.py --output path/to/out.json
    python import_species_csv.py --dry-run               # validate only, no output
    python import_species_csv.py --pretty                # pretty-print JSON (default)
    python import_species_csv.py --compact               # minified JSON

Design goals
------------
- Platform-agnostic: stdlib only (csv, json, argparse, pathlib, logging)
- No Flask, no SQLAlchemy, no pandas — runs in any Python 3.8+ environment
- Clear separation between parsing, validation, and serialisation
- Produces a diff-friendly report before writing
- Idempotent: running twice with the same input produces the same output
"""

import argparse
import csv
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()

# Column positions in the CSV (0-indexed, after the two header rows)
COL_SCIENTIFIC       = 0
COL_COMMERCIAL       = 1
COL_ALT_COMMERCIAL   = 2
COL_ENGLISH          = 3
COL_ALT_ENGLISH      = 4
COL_SWEDISH          = 5
COL_ALT_SWEDISH      = 6
COL_PORTUGUESE       = 7
COL_ALT_PORTUGUESE   = 8
COL_ORIGIN           = 9
COL_CITES            = 10

# Valid CITES appendix values (I, II, III or empty)
VALID_CITES_APPENDICES = {"I", "II", "III"}

# Rows to skip at the top of the file (title row + header row)
HEADER_ROWS_TO_SKIP = 2


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SpeciesRecord:
    """
    Canonical representation of a single wood species row.

    Field names mirror the Luthia `species` database table so this JSON
    can be used directly as a seed source for models.py without translation.
    """
    scientific_name:    str
    commercial_name:    str
    alt_commercial_name: Optional[str]
    english_name:       Optional[str]
    alt_english_name:   Optional[str]
    swedish_name:       Optional[str]
    alt_swedish_name:   Optional[str]
    portuguese_name:    Optional[str]
    alt_portuguese_name: Optional[str]
    origin:             Optional[str]
    cites_listed:       Optional[str]   # "I" | "II" | "III" | None

    # Computed at parse time — all non-empty alternate names collapsed into
    # a flat list for easy alias-table population.
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict, aliases included."""
        d = asdict(self)
        return d


def _str_or_none(value: str) -> Optional[str]:
    """Strip whitespace; return None for empty strings."""
    stripped = value.strip()
    return stripped if stripped else None


def _collect_aliases(record: SpeciesRecord) -> list[str]:
    """
    Gather every alternate name variant into a deduplicated alias list.
    The commercial_name and english_name are the primary names and are
    NOT included here — only the *alt_* fields and swedish/portuguese
    variants that differ from the primary.
    """
    candidates = [
        record.alt_commercial_name,
        record.alt_english_name,
        record.swedish_name,
        record.alt_swedish_name,
        record.portuguese_name,
        record.alt_portuguese_name,
    ]
    seen = set()
    aliases = []
    for name in candidates:
        if name and name not in seen:
            seen.add(name)
            aliases.append(name)
    return aliases


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class ParseError(Exception):
    """Raised when a row cannot be parsed into a valid SpeciesRecord."""


def parse_row(row: list[str], line_number: int) -> SpeciesRecord:
    """
    Parse a single CSV data row into a SpeciesRecord.

    Raises ParseError for rows that are structurally invalid (missing
    required fields). Validation warnings are returned separately by
    validate_record().
    """
    # Pad short rows so index access is always safe
    padded = row + [""] * (COL_CITES + 1)

    scientific = _str_or_none(padded[COL_SCIENTIFIC])
    if not scientific:
        raise ParseError(f"Line {line_number}: missing scientific name — row skipped")

    cites_raw = _str_or_none(padded[COL_CITES])

    record = SpeciesRecord(
        scientific_name     = scientific,
        commercial_name     = _str_or_none(padded[COL_COMMERCIAL]) or scientific,
        alt_commercial_name = _str_or_none(padded[COL_ALT_COMMERCIAL]),
        english_name        = _str_or_none(padded[COL_ENGLISH]),
        alt_english_name    = _str_or_none(padded[COL_ALT_ENGLISH]),
        swedish_name        = _str_or_none(padded[COL_SWEDISH]),
        alt_swedish_name    = _str_or_none(padded[COL_ALT_SWEDISH]),
        portuguese_name     = _str_or_none(padded[COL_PORTUGUESE]),
        alt_portuguese_name = _str_or_none(padded[COL_ALT_PORTUGUESE]),
        origin              = _str_or_none(padded[COL_ORIGIN]),
        cites_listed        = cites_raw,
    )
    record.aliases = _collect_aliases(record)
    return record


def validate_record(record: SpeciesRecord) -> list[str]:
    """
    Return a list of warning strings for a parsed record.
    Warnings do NOT prevent the record from being included in output.
    """
    warnings = []
    if not record.commercial_name:
        warnings.append("missing commercial_name")
    if record.cites_listed and record.cites_listed not in VALID_CITES_APPENDICES:
        warnings.append(
            f"unrecognised CITES value '{record.cites_listed}' "
            f"(expected one of {sorted(VALID_CITES_APPENDICES)})"
        )
    if not record.origin:
        warnings.append("missing origin")
    return warnings


# ---------------------------------------------------------------------------
# Import pipeline
# ---------------------------------------------------------------------------

@dataclass
class ImportResult:
    records:  list[SpeciesRecord] = field(default_factory=list)
    skipped:  list[str]           = field(default_factory=list)   # parse errors
    warnings: list[str]           = field(default_factory=list)   # validation issues
    cites_count: int              = 0


def import_csv(source: Path) -> ImportResult:
    """
    Read the species CSV and return an ImportResult.

    The CSV has two rows before the data starts:
      Row 0 — title banner  ("TONEWOOD SPECIES - NAMING REFERENCE")
      Row 1 — column headers ("SCIENTIFIC NAME", "COMMERCIAL NAME", …)
    """
    result = ImportResult()
    seen_scientific: set[str] = set()

    log.info("Reading: %s", source)

    with source.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        for line_number, row in enumerate(reader, start=1):

            # Skip the title and header rows
            if line_number <= HEADER_ROWS_TO_SKIP:
                log.debug("Skipping header row %d: %s", line_number, row[:2])
                continue

            # Skip completely blank rows (can appear at end of file)
            if not any(cell.strip() for cell in row):
                log.debug("Skipping blank row %d", line_number)
                continue

            # --- Parse ---
            try:
                record = parse_row(row, line_number)
            except ParseError as exc:
                msg = str(exc)
                log.warning(msg)
                result.skipped.append(msg)
                continue

            # --- Duplicate guard ---
            if record.scientific_name in seen_scientific:
                msg = f"Line {line_number}: duplicate scientific name '{record.scientific_name}' — skipped"
                log.warning(msg)
                result.skipped.append(msg)
                continue
            seen_scientific.add(record.scientific_name)

            # --- Validate ---
            row_warnings = validate_record(record)
            for w in row_warnings:
                msg = f"Line {line_number} ({record.scientific_name}): {w}"
                log.warning(msg)
                result.warnings.append(msg)

            # --- Accumulate ---
            if record.cites_listed:
                result.cites_count += 1
            result.records.append(record)

    return result


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def build_output_document(result: ImportResult, source: Path) -> dict:
    """
    Wrap the species list in a metadata envelope.

    The envelope makes the JSON self-describing and adds provenance so
    that consumers know where the data came from and how fresh it is.
    """
    return {
        "meta": {
            "title":        "Luthia — Wood Species Reference",
            "description":  "Canonical species naming data for the Luthia tonewood platform",
            "source_file":  source.name,
            "generated":    date.today().isoformat(),
            "schema_version": "1.0",
            "record_count": len(result.records),
            "cites_listed": result.cites_count,
        },
        "species": [r.to_dict() for r in result.records],
    }


def write_json(document: dict, destination: Path, pretty: bool = True) -> None:
    """Serialise the document to JSON and write to disk."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if pretty else None
    with destination.open("w", encoding="utf-8") as fh:
        json.dump(document, fh, ensure_ascii=False, indent=indent)
    log.info("Written: %s  (%s)", destination, _human_size(destination.stat().st_size))


def _human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n_bytes < 1024:
            return f"{n_bytes:.0f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} GB"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(result: ImportResult, destination: Path, dry_run: bool) -> None:
    """Print a diff-style summary to stdout."""
    sep = "─" * 60
    print(f"\n{sep}")
    print("  Luthia · Species Import Report")
    print(sep)
    print(f"  ✔  Records imported : {len(result.records)}")
    print(f"  ⚠  CITES listed     : {result.cites_count}")
    print(f"  ✘  Rows skipped     : {len(result.skipped)}")
    print(f"  ⚡  Warnings         : {len(result.warnings)}")

    if result.skipped:
        print("\n  Skipped rows:")
        for s in result.skipped:
            print(f"    • {s}")

    if result.warnings:
        print("\n  Validation warnings:")
        for w in result.warnings:
            print(f"    ⚠  {w}")

    if dry_run:
        print(f"\n  DRY RUN — no file written")
    else:
        print(f"\n  Output: {destination}")

    print(sep + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="import_species_csv",
        description=(
            "Convert the Luthia species CSV to a structured JSON file.\n"
            "Produces a metadata envelope + flat species array."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=SCRIPT_DIR / "data-sources" / "tonewood-species.csv",
        metavar="CSV",
        help="Path to the source CSV file (default: data-sources/tonewood-species.csv)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=SCRIPT_DIR / "data-sources" / "species.json",
        metavar="JSON",
        help="Destination JSON file path (default: data-sources/tonewood-species.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate without writing any output",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Write minified JSON instead of pretty-printed",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show DEBUG-level log output",
    )
    return parser


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)-8s %(message)s",
        stream=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    configure_logging(args.verbose)

    # --- Validate input path ---
    if not args.input.exists():
        log.error("Input file not found: %s", args.input)
        return 1

    # --- Import ---
    result = import_csv(args.input)

    if not result.records:
        log.error("No records parsed — aborting")
        return 1

    # --- Serialise ---
    document = build_output_document(result, args.input)

    # --- Report ---
    print_report(result, args.output, args.dry_run)

    # --- Write ---
    if not args.dry_run:
        write_json(document, args.output, pretty=not args.compact)

    return 0 if not result.skipped else 2


# Module-level logger (configured in main)
log = logging.getLogger(__name__)

if __name__ == "__main__":
    sys.exit(main())

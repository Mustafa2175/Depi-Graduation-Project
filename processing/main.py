"""Processing pipeline: Bronze (raw contract JSON) -> Silver (clean CSV).

Source-agnostic by design: it discovers every ``data/raw/<source>/<date>``
file, cleans each record through the single :mod:`processing.cleaner`,
applies a validation quality gate (quarantining bad rows), and writes the
Silver layer plus a per-run quality report. A manifest makes reprocessing
idempotent.

Paths are configurable via environment variables so tests can run against
an isolated workspace without touching real data:
    RAW_DIR, SILVER_DIR, FAILED_DIR, REPORT_DIR, MANIFEST_PATH
"""
from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd

from processing.cleaner import clean_file
from processing.validation.validator import DataValidator

RAW_DIR = os.getenv("RAW_DIR", "data/raw")
SILVER_DIR = os.getenv("SILVER_DIR", "data/silver")
FAILED_DIR = os.getenv("FAILED_DIR", "data/failed")
REPORT_DIR = os.getenv("REPORT_DIR", "data/reports")
MANIFEST_PATH = os.getenv("MANIFEST_PATH", "data/meta/manifest.json")


def quality_gate(df: pd.DataFrame):
    """Split a cleaned DataFrame into (valid, invalid) via DataValidator.

    Invalid rows get a ``validation_errors`` column and are quarantined
    instead of polluting the Silver layer.
    """
    valid_idx, invalid_rows = [], []
    for index, row in df.iterrows():
        errors = DataValidator.validate_row(row)
        if errors:
            row_dict = row.to_dict()
            row_dict["validation_errors"] = "|".join(errors)
            invalid_rows.append(row_dict)
        else:
            valid_idx.append(index)
    return df.loc[valid_idx], pd.DataFrame(invalid_rows)


def load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"processed_files": []}


def save_manifest(manifest: dict) -> None:
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)


def _iter_raw_files(manifest: dict):
    """Yield (source, date_dir, file_name, full_path) for unprocessed files."""
    if not os.path.isdir(RAW_DIR):
        return
    for source in sorted(os.listdir(RAW_DIR)):
        source_path = os.path.join(RAW_DIR, source)
        if not os.path.isdir(source_path):
            continue
        for date_dir in sorted(os.listdir(source_path)):
            date_path = os.path.join(source_path, date_dir)
            if not os.path.isdir(date_path):
                continue
            for file_name in sorted(os.listdir(date_path)):
                if not file_name.endswith(".json"):
                    continue
                key = f"{source}/{date_dir}/{file_name}"
                if key not in manifest["processed_files"]:
                    yield source, date_dir, file_name, os.path.join(date_path, file_name)


def run_pipeline() -> dict:
    manifest = load_manifest()
    report = {
        "run_at": str(datetime.now()),
        "total": 0,
        "valid": 0,
        "quarantined": 0,
        "files": [],
    }

    for source, date_dir, file_name, full_path in _iter_raw_files(manifest):
        print(f"🚀 Processing {source}: {file_name}")
        cleaned = clean_file(full_path)
        if not cleaned:
            manifest["processed_files"].append(f"{source}/{date_dir}/{file_name}")
            continue

        df = pd.DataFrame(cleaned)
        valid_df, invalid_df = quality_gate(df)

        output_file = file_name.replace(".json", ".csv")
        silver_dir = os.path.join(SILVER_DIR, source, date_dir)
        os.makedirs(silver_dir, exist_ok=True)
        valid_df.to_csv(
            os.path.join(silver_dir, output_file), index=False, encoding="utf-8-sig"
        )

        if not invalid_df.empty:
            failed_dir = os.path.join(FAILED_DIR, source, date_dir)
            os.makedirs(failed_dir, exist_ok=True)
            invalid_df.to_csv(
                os.path.join(failed_dir, f"failed_{output_file}"),
                index=False,
                encoding="utf-8-sig",
            )

        report["total"] += len(df)
        report["valid"] += len(valid_df)
        report["quarantined"] += len(invalid_df)
        report["files"].append(
            {
                "file": f"{source}/{date_dir}/{file_name}",
                "records": len(df),
                "valid": len(valid_df),
                "quarantined": len(invalid_df),
            }
        )
        manifest["processed_files"].append(f"{source}/{date_dir}/{file_name}")
        print(
            f"✅ Saved to Silver: {output_file} "
            f"({len(valid_df)} valid, {len(invalid_df)} quarantined)"
        )

    save_manifest(manifest)

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = os.path.join(
        REPORT_DIR, f"processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(
        f"\n🏁 Processing complete — {report['valid']} valid, "
        f"{report['quarantined']} quarantined of {report['total']} records. "
        f"Report: {report_file}"
    )
    return report


if __name__ == "__main__":
    run_pipeline()

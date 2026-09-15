#!/usr/bin/env python3
"""Validate repository YAML syntax and required Kubernetes object fields.

This script does not contact a Kubernetes API or modify files. It parses all
tracked YAML files and enforces apiVersion/kind only for Kubernetes manifest
directories. Helm values files are syntax-checked but intentionally exempt.
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_MARKERS = {"k8s", "manifests", "dashboard", "application"}
EXCLUDED_PARTS = {".git", ".venv"}


def is_manifest(path: Path) -> bool:
    return any(part in MANIFEST_MARKERS for part in path.parts)


def yaml_files() -> list[Path]:
    candidates = [*REPO_ROOT.rglob("*.yaml"), *REPO_ROOT.rglob("*.yml")]
    return sorted(path for path in candidates if not EXCLUDED_PARTS.intersection(path.parts))


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    except yaml.YAMLError as exc:
        return [f"{display_path(path)}: YAML parse error: {exc}"]

    for index, document in enumerate(documents, start=1):
        if document is None:
            continue
        if not isinstance(document, dict):
            errors.append(f"{display_path(path)} document {index}: expected a YAML mapping.")
            continue
        if is_manifest(path):
            for field in ("apiVersion", "kind"):
                if not document.get(field):
                    errors.append(f"{display_path(path)} document {index}: missing required field {field}.")
    return errors


def display_path(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse lab YAML files without contacting Kubernetes.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional YAML files to validate instead of the repository set.")
    args = parser.parse_args()

    files = sorted(args.paths) if args.paths else yaml_files()
    errors = [error for path in files for error in validate_file(path)]

    if errors:
        print("YAML validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1

    print(f"YAML validation passed: {len(files)} files parsed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

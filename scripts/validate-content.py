#!/usr/bin/env python3
"""Validate Vauchi content files against JSON schemas.

Validates all content files in app-files-src/ against their schemas.

Usage:
    python scripts/validate-content.py [--src SRC]
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("Error: jsonschema package required. Install with: pip install jsonschema")
    sys.exit(1)


def load_json(path: Path) -> dict:
    """Load and parse a JSON file."""
    with open(path) as f:
        return json.load(f)


def validate_file(file_path: Path, schema_path: Path) -> list[str]:
    """Validate a JSON file against a schema. Returns list of errors."""
    errors = []

    try:
        data = load_json(file_path)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    try:
        schema = load_json(schema_path)
    except json.JSONDecodeError as e:
        return [f"Invalid schema JSON: {e}"]

    validator = Draft202012Validator(schema)
    for error in validator.iter_errors(data):
        path = ".".join(str(p) for p in error.path) if error.path else "(root)"
        errors.append(f"  {path}: {error.message}")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate Vauchi content files")
    parser.add_argument(
        "--src",
        default="app-files-src",
        help="Source directory (default: app-files-src)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    src_dir = root_dir / args.src
    schemas_dir = src_dir / "schemas"

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        return 1

    if not schemas_dir.exists():
        print(f"Error: Schemas directory not found: {schemas_dir}")
        return 1

    validations = [
        ("networks.json", "networks.schema.json"),
    ]

    # Add all locale files
    locales_dir = src_dir / "locales"
    if locales_dir.exists():
        for locale_file in locales_dir.glob("*.json"):
            rel_path = f"locales/{locale_file.name}"
            validations.append((rel_path, "locales.schema.json"))

    all_valid = True
    for content_file, schema_file in validations:
        content_path = src_dir / content_file
        schema_path = schemas_dir / schema_file

        if not content_path.exists():
            print(f"SKIP {content_file} (not found)")
            continue

        if not schema_path.exists():
            print(f"SKIP {content_file} (schema not found: {schema_file})")
            continue

        errors = validate_file(content_path, schema_path)

        if errors:
            print(f"FAIL {content_file}")
            for error in errors:
                print(error)
            all_valid = False
        else:
            print(f"OK   {content_file}")

    if all_valid:
        print("\nAll validations passed!")
        return 0
    else:
        print("\nValidation failed!")
        return 1


if __name__ == "__main__":
    exit(main())

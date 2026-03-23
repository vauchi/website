#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Build localized landing pages from a single Jinja2 template + i18n JSON files.

Usage:
    python scripts/build-pages.py                  # build all locales
    python scripts/build-pages.py --validate-only   # check translations only
    python scripts/build-pages.py --locale fr       # build one locale

Reads:
    templates/index.html     — Jinja2 template
    i18n/en.json             — canonical English strings (all keys must exist here)
    i18n/{lang}.json         — translations

Writes:
    public/index.html        — English (default)
    public/{lang}/index.html — each additional locale
"""

import json
import os
import sys

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:
    print("ERROR: jinja2 not installed. Run: pip install jinja2", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N_DIR = os.path.join(ROOT, "i18n")
TEMPLATE_DIR = os.path.join(ROOT, "templates")
PUBLIC_DIR = os.path.join(ROOT, "public")

DEFAULT_LOCALE = "en"


def load_translations(locale: str) -> dict:
    """Load a locale JSON file."""
    path = os.path.join(I18N_DIR, f"{locale}.json")
    if not os.path.exists(path):
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def discover_locales() -> list[str]:
    """Find all locale JSON files."""
    locales = []
    for f in sorted(os.listdir(I18N_DIR)):
        if f.endswith(".json"):
            locales.append(f[:-5])
    return locales


def validate_translations(en: dict, locales: dict[str, dict]) -> list[str]:
    """Check that every EN key exists in every locale. Returns list of errors."""
    errors = []
    en_keys = set(en.keys())

    for lang, trans in locales.items():
        if lang == DEFAULT_LOCALE:
            continue
        trans_keys = set(trans.keys())
        missing = en_keys - trans_keys
        extra = trans_keys - en_keys
        if missing:
            errors.append(f"{lang}.json: missing {len(missing)} keys: {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}")
        if extra:
            # Extra keys are warnings, not errors
            print(f"  WARN: {lang}.json has {len(extra)} extra keys: {sorted(extra)[:5]}", file=sys.stderr)

    return errors


def build_player_i18n(translations: dict) -> str:
    """Build the player i18n JSON block from translation keys starting with 'player.'."""
    player_data = {}
    for k, v in translations.items():
        if k.startswith("player."):
            player_data[k[7:]] = v  # strip "player." prefix
    return json.dumps(player_data, indent=6, ensure_ascii=False)


def build_page(env: Environment, locale: str, translations: dict) -> str:
    """Render the template for a given locale."""
    template = env.get_template("index.html")
    return template.render(
        t=translations,
        lang=locale,
        is_default=(locale == DEFAULT_LOCALE),
        player_i18n=build_player_i18n(translations),
    )


def write_page(locale: str, html: str):
    """Write generated HTML to the correct public path."""
    if locale == DEFAULT_LOCALE:
        path = os.path.join(PUBLIC_DIR, "index.html")
    else:
        dir_path = os.path.join(PUBLIC_DIR, locale)
        os.makedirs(dir_path, exist_ok=True)
        path = os.path.join(dir_path, "index.html")

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  {locale}: {path} ({len(html):,} bytes)")


def main():
    validate_only = "--validate-only" in sys.argv
    single_locale = None
    if "--locale" in sys.argv:
        idx = sys.argv.index("--locale")
        if idx + 1 < len(sys.argv):
            single_locale = sys.argv[idx + 1]

    # Load all translations
    locales = discover_locales()
    if not locales:
        print("ERROR: No locale files found in i18n/", file=sys.stderr)
        sys.exit(1)

    if DEFAULT_LOCALE not in locales:
        print(f"ERROR: Default locale {DEFAULT_LOCALE}.json not found", file=sys.stderr)
        sys.exit(1)

    all_translations = {}
    for locale in locales:
        all_translations[locale] = load_translations(locale)

    en = all_translations[DEFAULT_LOCALE]

    # Validate
    print(f"Validating {len(locales)} locales ({', '.join(locales)})...")
    errors = validate_translations(en, all_translations)
    if errors:
        print("\nERROR: Translation validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  All locales have {len(en)} keys. Validation passed.")

    if validate_only:
        print("Validation-only mode. Skipping page generation.")
        return

    # Build pages
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,  # fail on missing keys in template
        autoescape=False,  # HTML template, not user input
        keep_trailing_newline=True,
    )

    targets = [single_locale] if single_locale else locales
    print(f"\nBuilding {len(targets)} page(s)...")
    for locale in targets:
        html = build_page(env, locale, all_translations[locale])
        write_page(locale, html)

    print(f"\nDone. {len(targets)} page(s) generated.")


if __name__ == "__main__":
    main()

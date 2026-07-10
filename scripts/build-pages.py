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
import re
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
VARIANT_IDS = ["a", "b", "c", "d", "e", "f", "g"]


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


def build_key_prefix_i18n(translations: dict, prefix: str) -> str:
    """Build a JSON block from translation keys starting with the given prefix."""
    data = {}
    prefix_len = len(prefix)
    for k, v in translations.items():
        if k.startswith(prefix):
            data[k[prefix_len:]] = v
    return json.dumps(data, indent=6, ensure_ascii=False)


def slugify(text: str) -> str:
    """Create a URL-safe slug from a headline."""
    s = text.lower()
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"&[^;]+;", "", s)
    s = re.sub(r"[^a-z0-9\s-]+", "", s)
    s = re.sub(r"[\s-]+", "-", s).strip("-")
    return s or "variant"


def get_variant_strings(translations: dict, variant_id: str) -> dict:
    """Extract label/headline/sub/cta for a single variant."""
    prefix = f"hero.variant.{variant_id}."
    return {
        k[len(prefix):]: v
        for k, v in translations.items()
        if k.startswith(prefix)
    }


def build_variants_manifest(all_translations: dict[str, dict]) -> dict:
    """Build a machine-readable manifest of all landing-page variants per locale."""
    manifest = {
        "default_locale": DEFAULT_LOCALE,
        "variants": {},
        "locales": {},
    }
    en = all_translations[DEFAULT_LOCALE]
    for variant_id in VARIANT_IDS:
        manifest["variants"][variant_id] = {
            "slug": slugify(get_variant_strings(en, variant_id).get("headline", "")),
            "default": get_variant_strings(en, variant_id),
        }
    for locale, trans in all_translations.items():
        variants = {}
        for variant_id in VARIANT_IDS:
            variants[variant_id] = get_variant_strings(trans, variant_id)
        manifest["locales"][locale] = variants
    return manifest


def write_variants_manifest(manifest: dict):
    """Write the variants manifest to public/variants.json."""
    path = os.path.join(PUBLIC_DIR, "variants.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  variants: {path}")


def write_short_links(manifest: dict):
    """Write /l/<variant> redirect pages to the variant landing pages.

    Generated from the same slug source as the landing pages, so the
    short links follow automatically when a headline (and thus its
    slug) changes.
    """
    for variant_id, info in manifest["variants"].items():
        target = f"/landing/{info['slug']}/"
        dir_path = os.path.join(PUBLIC_DIR, "l", variant_id)
        os.makedirs(dir_path, exist_ok=True)
        html = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            f'<meta http-equiv="refresh" content="0; url={target}">\n'
            f'<link rel="canonical" href="https://vauchi.app{target}">\n'
            "<title>Vauchi</title>\n"
            "</head>\n"
            f'<body><a href="{target}">Continue to Vauchi</a></body>\n'
            "</html>\n"
        )
        with open(os.path.join(dir_path, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
    ids = "|".join(manifest["variants"])
    print(f"  short links: /l/<{ids}>")


def build_page(
    env: Environment,
    locale: str,
    translations: dict,
    variant_id: str | None = None,
    variant_strings: dict | None = None,
    variant_slug: str | None = None,
) -> str:
    """Render the template for a given locale, optionally pinned to a variant."""
    template = env.get_template("index.html")
    return template.render(
        t=translations,
        lang=locale,
        is_default=(locale == DEFAULT_LOCALE),
        player_i18n=build_key_prefix_i18n(translations, "player."),
        variant_i18n=build_key_prefix_i18n(translations, "hero.variant."),
        variant_id=variant_id,
        variant_strings=variant_strings,
        variant_slug=variant_slug,
    )


def write_page(locale: str, html: str, variant_slug: str | None = None):
    """Write generated HTML to the correct public path."""
    if variant_slug:
        dir_path = os.path.join(PUBLIC_DIR, "landing", variant_slug)
        if locale != DEFAULT_LOCALE:
            dir_path = os.path.join(dir_path, locale)
    elif locale == DEFAULT_LOCALE:
        path = os.path.join(PUBLIC_DIR, "index.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  {locale}: {path} ({len(html):,} bytes)")
        return
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

    # Build per-variant landing pages for accurate SEO/social previews.
    # Each page is pre-rendered with the variant headline/sub in the meta,
    # Open Graph, and JSON-LD tags so crawlers see the exact slogan.
    print("\nBuilding variant landing pages...")
    for locale in targets:
        trans = all_translations[locale]
        for variant_id in VARIANT_IDS:
            strings = get_variant_strings(trans, variant_id)
            slug = slugify(get_variant_strings(en, variant_id).get("headline", ""))
            html = build_page(
                env,
                locale,
                trans,
                variant_id=variant_id,
                variant_strings=strings,
                variant_slug=slug,
            )
            write_page(locale, html, variant_slug=slug)

    # Always write the full variants manifest (not locale-scoped) so crawlers
    # can discover every slogan without executing JavaScript.
    manifest = build_variants_manifest(all_translations)
    write_variants_manifest(manifest)
    write_short_links(manifest)

    total_pages = len(targets) + (len(targets) * len(VARIANT_IDS))
    print(f"\nDone. {total_pages} page(s) generated.")


if __name__ == "__main__":
    main()

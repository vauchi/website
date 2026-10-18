# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Shared translations for the public site and its optional mail campaign."""

from functools import lru_cache
import json
from pathlib import Path
from urllib.parse import urljoin

from flask import render_template, request

LOCALES = frozenset(("en", "de", "fr", "it", "es"))
RESOURCE_DIR = Path(__file__).parent / "i18n"
if not RESOURCE_DIR.is_dir():
    RESOURCE_DIR = Path(__file__).parents[1] / "i18n"


def language():
    selected = request.form.get("lang") if request.method == "POST" else request.args.get("lang")
    return selected if selected in LOCALES else "en"


@lru_cache(maxsize=5)
def translations(locale):
    selected = locale if locale in LOCALES else "en"
    return json.loads((RESOURCE_DIR / f"{selected}.json").read_text(encoding="utf-8"))


def home(base, locale):
    return urljoin(base, "/" if locale == "en" else f"/{locale}/")


def management_page(base, pending_days, confirmed_days, *, token=None, result=None):
    locale = language()
    text = translations(locale)
    return render_template("manage.html", lang=locale, t=text, token=token, result=result,
        home=home(base, locale), retention=text["waitlist.manage.retention"].format(
            pending_days=pending_days, confirmed_days=confirmed_days))

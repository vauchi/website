# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import re
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from markupsafe import escape

from service_fixture import ServiceTestCase, api


LABELS = {
    "en": ("Email address", "Leave the waitlist", "Confirm your spot on the Vauchi waitlist"),
    "de": ("E-Mail-Adresse", "Von der Warteliste abmelden", "Bestätige deinen Platz auf der Vauchi-Warteliste"),
    "fr": ("Adresse e-mail", "Quitter la liste d’attente", "Confirmez votre inscription à la liste d’attente Vauchi"),
    "it": ("Indirizzo email", "Esci dalla lista d’attesa", "Conferma l’iscrizione alla lista d’attesa di Vauchi"),
    "es": ("Dirección de correo electrónico", "Salir de la lista de espera", "Confirma tu inscripción en la lista de espera de Vauchi"),
}


class LocalizedManagement(ServiceTestCase):
    def test_removal_pages_and_forms_keep_the_selected_language(self):
        for locale, (label, heading, _) in LABELS.items():
            with self.subTest(locale=locale):
                response = self.client.get(f"/waitlist/manage?lang={locale}")
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn(f'<html lang="{locale}">', html)
                self.assertIn(label, html)
                self.assertIn(heading, html)
                self.assertIn('for="waitlist-email"', html)
                self.assertIn('id="waitlist-email"', html)
                self.assertIn(f'name="lang" value="{locale}"', html)
                removed = self.client.post("/waitlist/withdraw", data={"lang": locale, "token": "unknown"})
                self.assertEqual(removed.status_code, 200)
                self.assertIn(f'<html lang="{locale}">', removed.get_data(as_text=True))

    def test_confirmation_mail_and_result_keep_the_selected_language(self):
        with patch.object(api, "CONFIRMATION_SUBJECT", ""):
            for locale, (_, _, subject) in LABELS.items():
                with self.subTest(locale=locale):
                    response = self.client.post("/waitlist/join", data={
                        "email": f"{locale}@example.test", "lang": locale,
                    })
                    self.assertEqual(response.status_code, 303)
                    message = self.mail.messages[-1]
                    self.assertEqual(message["Subject"], subject)
                    links = re.findall(r"https://[^\s]+/waitlist/[^\s]+", message.get_content())
                    self.assertEqual(len(links), 2)
                    for link in links:
                        self.assertEqual(parse_qs(urlparse(link).query)["lang"], [locale])
                    confirmation = next(link for link in links if "/confirm?" in link)
                    result = self.client.get(confirmation)
                    self.assertEqual(result.status_code, 200)
                    self.assertIn(f'<html lang="{locale}">', result.get_data(as_text=True))
                    self.assertIn(api.translations(locale)['waitlist.message.confirmed'], result.get_data(as_text=True))

    def test_management_pages_carry_preview_metadata_and_stay_out_of_search(self):
        for locale in LABELS:
            with self.subTest(locale=locale):
                html = self.client.get(f"/waitlist/manage?lang={locale}").get_data(as_text=True)
                description = escape(api.translations(locale)["waitlist.manage.description"])
                canonical = api.REDIRECT_BASE + "waitlist/manage" + ("" if locale == "en" else f"?lang={locale}")
                self.assertIn('<meta name="robots" content="noindex">', html)
                self.assertIn(f'<meta name="description" content="{description}">', html)
                self.assertIn(f'<meta property="og:description" content="{description}">', html)
                self.assertIn(f'<link rel="canonical" href="{canonical}">', html)
                self.assertIn(f'<meta property="og:url" content="{canonical}">', html)
                self.assertIn('<meta property="og:image" content="https://vauchi.app/social-preview.png">', html)
                self.assertIn('<link rel="stylesheet" href="/css/page.css">', html)

    def test_a_withdrawal_page_never_names_its_token_in_metadata(self):
        html = self.client.get("/waitlist/withdraw?token=secret-token-123&lang=de").get_data(as_text=True)
        head = html.split("</head>")[0]
        self.assertNotIn("secret-token-123", head)
        self.assertIn(f'<link rel="canonical" href="{api.REDIRECT_BASE}waitlist/manage?lang=de">', head)

    def test_a_trailing_slash_reaches_the_management_page_with_its_query(self):
        response = self.client.get("/waitlist/manage/?lang=fr")
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.headers["Location"], "/waitlist/manage?lang=fr")

    def test_unknown_language_cannot_select_an_arbitrary_resource(self):
        response = self.client.get("/waitlist/manage?lang=../../untrusted")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html lang="en">', response.get_data(as_text=True))

    def test_untrusted_removal_link_is_escaped_and_cannot_execute_inline_scripts(self):
        payload = '\"><script>alert("synthetic")</script>'
        response = self.client.get("/waitlist/withdraw", query_string={"token": payload})
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("default-src 'none'", response.headers["Content-Security-Policy"])
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
        self.assertNotIn("script-src 'unsafe-inline'", response.headers["Content-Security-Policy"])

# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import re
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

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

    def test_confirmation_mail_and_redirect_keep_the_selected_language(self):
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
                    path = "" if locale == "en" else locale + "/"
                    self.assertEqual(result.headers["Location"], f"https://vauchi.app/{path}?waitlist=confirmed#waitlist")

    def test_unknown_language_cannot_select_an_arbitrary_resource(self):
        response = self.client.get("/waitlist/manage?lang=../../untrusted")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html lang="en">', response.get_data(as_text=True))

    def test_untrusted_removal_link_is_escaped_and_does_not_enable_scripts(self):
        payload = '\"><script>alert("synthetic")</script>'
        response = self.client.get("/waitlist/withdraw", query_string={"token": payload})
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("default-src 'none'", response.headers["Content-Security-Policy"])
        self.assertNotIn("script-src", response.headers["Content-Security-Policy"])

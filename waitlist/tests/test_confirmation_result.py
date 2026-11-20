# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

from markupsafe import escape

from service_fixture import ServiceTestCase, api


class ConfirmationResult(ServiceTestCase):
    def test_invalid_confirmation_is_a_script_free_result_not_a_redirect(self):
        response = self.client.get('/waitlist/confirm?token=synthetic-invalid&lang=de')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Location', response.headers)
        html = response.get_data(as_text=True)
        self.assertIn('<html lang="de">', html)
        self.assertIn(api.translations('de')['waitlist.message.invalid_token'], html)
        self.assertNotIn('<script', html)
        self.assertNotIn('synthetic-invalid', html)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
        self.assertIn("default-src 'none'", response.headers['Content-Security-Policy'])

    def test_confirmation_pages_stay_out_of_search_and_describe_themselves(self):
        for locale in ("en", "de", "fr", "it", "es"):
            with self.subTest(locale=locale):
                html = self.client.get(f"/waitlist/confirm?token=synthetic-token-42&lang={locale}").get_data(as_text=True)
                head = html.split("</head>")[0]
                description = escape(api.translations(locale)["waitlist.confirm.description"])
                self.assertIn('<meta name="robots" content="noindex">', head)
                self.assertIn(f'<meta name="description" content="{description}">', head)
                self.assertNotIn("synthetic-token-42", html)

    def test_the_waitlist_root_leads_to_the_signup_on_the_landing_page(self):
        for query, target in (("", "/#waitlist"), ("?lang=fr", "/fr/#waitlist"), ("?lang=../x", "/#waitlist")):
            with self.subTest(query=query):
                response = self.client.get("/waitlist/" + query)
                # 302: the landing section it points at may move.
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], target)

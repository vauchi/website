# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

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

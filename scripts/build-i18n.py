#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate translated versions of the Vauchi landing page.

Usage:
    python scripts/build-i18n.py

Reads public/index.html (English source) and generates:
    public/fr/index.html
    public/de/index.html
    public/it/index.html

Also patches public/index.html with hreflang links and language picker.
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
PUBLIC_DIR = os.path.join(WEBSITE_DIR, "public")
SOURCE_FILE = os.path.join(PUBLIC_DIR, "index.html")

LANGUAGES = ["en", "fr", "de", "it"]
LANG_LABELS = {"en": "EN", "fr": "FR", "de": "DE", "it": "IT"}

HREFLANG_BLOCK = """\
    <link rel="alternate" hreflang="en" href="https://vauchi.app/" />
    <link rel="alternate" hreflang="fr" href="https://vauchi.app/fr/" />
    <link rel="alternate" hreflang="de" href="https://vauchi.app/de/" />
    <link rel="alternate" hreflang="it" href="https://vauchi.app/it/" />
    <link rel="alternate" hreflang="x-default" href="https://vauchi.app/" />"""


def lang_picker_html(active_lang):
    """Generate the language picker HTML with the active language highlighted."""
    parts = []
    for lang in LANGUAGES:
        href = "/" if lang == "en" else f"/{lang}/"
        if lang == active_lang:
            style = "color:var(--accent);text-decoration:none;font-weight:600"
        else:
            style = "color:var(--text-secondary);text-decoration:none"
        parts.append(f'<a href="{href}" style="{style}">{LANG_LABELS[lang]}</a>')
    inner = ' <span style="color:var(--border)">\u00b7</span> '.join(parts)
    return (
        f'<div style="display:flex;gap:6px;margin-left:12px;font-size:0.8rem">'
        f"{inner}</div>"
    )


# ---------------------------------------------------------------------------
# Translations: list of (search, replace) pairs per language.
# Order matters: longer/more-specific patterns first to avoid partial matches.
# ---------------------------------------------------------------------------

# Common regex: tagline that may span two lines in the footer
TAGLINE_EN = r"Auditable &#xB7; End-to-End Encrypted &#xB7; No Accounts\s+Required"

FR = {
    "tagline_regex": "Auditable &#xB7; Chiffr\u00e9 de bout en bout &#xB7; Aucun compte requis",
    "pairs": [
        # --- HTML lang & title ---
        ('<html lang="en">', '<html lang="fr">'),
        (
            "<title>Vauchi - Privacy-First Contact Exchange</title>",
            "<title>Vauchi - \u00c9change de contacts confidentiel</title>",
        ),
        # --- Scene 0: Intro ---
        (
            "The last time you'll ever exchange contact info.",
            "La derni\u00e8re fois que vous \u00e9changerez vos coordonn\u00e9es.",
        ),
        (">End-to-End Encrypted<", ">Chiffr\u00e9 de bout en bout<"),
        (">No Accounts<", ">Sans compte<"),
        # Open Source stays same
        # --- Scene 1: Problem ---
        ("The Problem", "Le probl\u00e8me"),
        (
            "Your address book is a graveyard of dead contacts.",
            "Votre carnet d\u2019adresses est un cimeti\u00e8re de contacts obsol\u00e8tes.",
        ),
        ("+1 555-0147 (disconnected)", "+1 555-0147 (d\u00e9connect\u00e9)"),
        ("+44 7911 \u2588\u2588\u2588\u2588 (old number)", "+44 7911 \u2588\u2588\u2588\u2588 (ancien num\u00e9ro)"),
        ("@jordan.p (deleted)", "@jordan.p (supprim\u00e9)"),
        ("sound familiar?", "\u00e7a vous dit quelque chose\u202f?"),
        # --- Scene 2: Exchange ---
        ("Contact Exchange", "\u00c9change de contacts"),
        ("Meet in person. Scan. Connected.", "Rencontrez-vous. Scannez. Connect\u00e9s."),
        ('>YOU<', '>VOUS<'),
        ('class="v-micro">Show QR<', 'class="v-micro">Afficher QR<'),
        ('class="v-micro">Scan<', 'class="v-micro">Scanner<'),
        (
            "No phone number or account needed",
            "Aucun num\u00e9ro de t\u00e9l\u00e9phone ni compte requis",
        ),
        # --- Scene 3: Exchanged ---
        (
            "Both phones now hold each other's encrypted contact card.",
            "Les deux t\u00e9l\u00e9phones d\u00e9tiennent maintenant la fiche contact chiffr\u00e9e de l\u2019autre.",
        ),
        (">YOUR PHONE<", ">VOTRE T\u00c9L\u00c9PHONE<"),
        (">ALEX'S PHONE<", ">T\u00c9L\u00c9PHONE D\u2019ALEX<"),
        ("exchange once", "\u00e9changez une fois"),
        ("stay connected", "restez connect\u00e9s"),
        # --- Scene 4: Silent Updates ---
        ("Silent Updates", "Mises \u00e0 jour silencieuses"),
        (
            "When your details change, your friends' phones update",
            "Quand vos coordonn\u00e9es changent, les t\u00e9l\u00e9phones de vos amis se mettent \u00e0 jour",
        ),
        (
            "automatically. No notifications, no noise.",
            "automatiquement. Aucune notification, aucun bruit.",
        ),
        (">YOU UPDATE<", ">VOUS METTEZ \u00c0 JOUR<"),
        (">ALEX SEES<", ">ALEX VOIT<"),
        ("no matter what changes", "peu importe ce qui change"),
        # --- Scene 5: Platform Freedom ---
        ("Platform Freedom", "Libert\u00e9 de plateforme"),
        (
            "Switch social networks? Change email providers? Your contacts stay",
            "Vous changez de r\u00e9seau social\u202f? De fournisseur e-mail\u202f? Vos contacts restent",
        ),
        ("              current.\n", "              \u00e0 jour.\n"),
        (">BEFORE<", ">AVANT<"),
        (">AFTER<", ">APR\u00c8S<"),
        ("update once", "mettez \u00e0 jour une fois"),
        ("everyone sees the change", "tout le monde voit le changement"),
        # --- Scene 6: Granular Privacy ---
        ("Granular Privacy", "Confidentialit\u00e9 granulaire"),
        (
            "Share work details with colleagues and home addresses with family",
            "Partagez vos coordonn\u00e9es professionnelles avec vos coll\u00e8gues et votre adresse personnelle avec votre famille",
        ),
        ("all from a single identity.", "le tout depuis une seule identit\u00e9."),
        ("Colleague sees", "Un coll\u00e8gue voit"),
        ("Family sees", "La famille voit"),
        (
            "&#x1F512; address, personal social hidden",
            "&#x1F512; adresse, r\u00e9seaux perso masqu\u00e9s",
        ),
        ("you control the visibility", "vous contr\u00f4lez la visibilit\u00e9"),
        # --- Scene 7: Physical Recovery ---
        ("Physical Recovery", "R\u00e9cup\u00e9ration physique"),
        (
            "No master passwords to lose. Regain access through in-person",
            "Aucun mot de passe ma\u00eetre \u00e0 perdre. Retrouvez l\u2019acc\u00e8s gr\u00e2ce \u00e0 une v\u00e9rification",
        ),
        (
            "verification with your trusted inner circle.",
            "en personne avec votre cercle de confiance.",
        ),
        ("lost device", "appareil perdu"),
        ("trusted circle", "cercle de confiance"),
        ("new device", "nouvel appareil"),
        ("in-person verification", "v\u00e9rification en personne"),
        ("no cloud, no passwords", "ni cloud, ni mots de passe"),
        # --- Scene 8: Zero Platform ---
        ("Zero Platform", "Z\u00e9ro plateforme"),
        (
            "No feeds, no profiles, no social graphs.",
            "Pas de flux, pas de profils, pas de graphes sociaux.",
        ),
        (">feeds<", ">flux<"),
        (">profiles<", ">profils<"),
        (">social graph<", ">graphe social<"),
        (
            "Open-source infrastructure you own entirely.",
            "Une infrastructure open source qui vous appartient enti\u00e8rement.",
        ),
        # --- Scene 9: Outro ---
        (
            "Exchange once. Stay connected",
            "\u00c9changez une fois. Restez connect\u00e9s",
        ),
        # --- Footer & links ---
        (">Demo (coming soon)<", ">D\u00e9mo (bient\u00f4t)<"),
        (">Sponsor<", ">Sponsoriser<"),
        (">Donate<", ">Donner<"),
        # --- ARIA labels ---
        ('"How Vauchi works"', '"Comment fonctionne Vauchi"'),
        ('"Toggle dark/light mode"', '"Basculer mode sombre/clair"'),
        ('"Choose theme"', '"Choisir le th\u00e8me"'),
        # --- i18n JSON: scene names ---
        ('"Intro"', '"Introduction"'),
        ('"Exchanged"', '"\u00c9chang\u00e9"'),
        ('"Outro"', '"Conclusion"'),
        # --- i18n JSON: dynamic text ---
        ('"txt_scanning": "scanning"', '"txt_scanning": "scan en cours"'),
        ('"txt_paired": "paired"', '"txt_paired": "jumel\u00e9"'),
        ('"txt_editing": "editing..."', '"txt_editing": "modification..."'),
        ('"txt_saved": "\\u2713 saved"', '"txt_saved": "\\u2713 enregistr\u00e9"'),
        ('"txt_auto_synced": "\\u2713 auto-synced"', '"txt_auto_synced": "\\u2713 synchronis\u00e9"'),
        ('"txt_waiting": "waiting..."', '"txt_waiting": "en attente..."'),
        ('"txt_restored": "\\u2713 restored"', '"txt_restored": "\\u2713 restaur\u00e9"'),
        ('"txt_new_device": "new device"', '"txt_new_device": "nouvel appareil"'),
        # --- Contact name ---
        ('class="v-contact-name">You<', 'class="v-contact-name">Vous<'),
        ('class="v-priv-name">You<', 'class="v-priv-name">Vous<'),
    ],
}

DE = {
    "tagline_regex": "\u00dcberpr\u00fcfbar &#xB7; Ende-zu-Ende-verschl\u00fcsselt &#xB7; Kein Konto n\u00f6tig",
    "pairs": [
        # --- HTML lang & title ---
        ('<html lang="en">', '<html lang="de">'),
        (
            "<title>Vauchi - Privacy-First Contact Exchange</title>",
            "<title>Vauchi - Privatsph\u00e4re-zuerst Kontaktaustausch</title>",
        ),
        # --- Scene 0: Intro ---
        (
            "The last time you'll ever exchange contact info.",
            "Das letzte Mal, dass Sie Kontaktdaten austauschen.",
        ),
        (">End-to-End Encrypted<", ">Ende-zu-Ende-verschl\u00fcsselt<"),
        (">No Accounts<", ">Keine Konten<"),
        # --- Scene 1: Problem ---
        ("The Problem", "Das Problem"),
        (
            "Your address book is a graveyard of dead contacts.",
            "Ihr Adressbuch ist ein Friedhof veralteter Kontakte.",
        ),
        ("+1 555-0147 (disconnected)", "+1 555-0147 (getrennt)"),
        ("+44 7911 \u2588\u2588\u2588\u2588 (old number)", "+44 7911 \u2588\u2588\u2588\u2588 (alte Nummer)"),
        ("@jordan.p (deleted)", "@jordan.p (gel\u00f6scht)"),
        ("sound familiar?", "kommt Ihnen das bekannt vor?"),
        # --- Scene 2: Exchange ---
        ("Contact Exchange", "Kontaktaustausch"),
        (
            "Meet in person. Scan. Connected.",
            "Pers\u00f6nlich treffen. Scannen. Verbunden.",
        ),
        ('>YOU<', '>SIE<'),
        ('class="v-micro">Show QR<', 'class="v-micro">QR zeigen<'),
        ('class="v-micro">Scan<', 'class="v-micro">Scannen<'),
        (
            "No phone number or account needed",
            "Keine Telefonnummer oder Konto n\u00f6tig",
        ),
        # --- Scene 3: Exchanged ---
        (
            "Both phones now hold each other's encrypted contact card.",
            "Beide Telefone haben jetzt die verschl\u00fcsselte Kontaktkarte des anderen.",
        ),
        (">YOUR PHONE<", ">IHR TELEFON<"),
        (">ALEX'S PHONE<", ">ALEX\u2019 TELEFON<"),
        ("exchange once", "einmal austauschen"),
        ("stay connected", "verbunden bleiben"),
        # --- Scene 4: Silent Updates ---
        ("Silent Updates", "Stille Updates"),
        (
            "When your details change, your friends' phones update",
            "Wenn sich Ihre Daten \u00e4ndern, aktualisieren sich die Telefone Ihrer Freunde",
        ),
        (
            "automatically. No notifications, no noise.",
            "automatisch. Keine Benachrichtigungen, kein L\u00e4rm.",
        ),
        (">YOU UPDATE<", ">SIE AKTUALISIEREN<"),
        (">ALEX SEES<", ">ALEX SIEHT<"),
        ("no matter what changes", "egal was sich \u00e4ndert"),
        # --- Scene 5: Platform Freedom ---
        ("Platform Freedom", "Plattform-Freiheit"),
        (
            "Switch social networks? Change email providers? Your contacts stay",
            "Soziale Netzwerke wechseln? E-Mail-Anbieter \u00e4ndern? Ihre Kontakte bleiben",
        ),
        ("              current.\n", "              aktuell.\n"),
        (">BEFORE<", ">VORHER<"),
        (">AFTER<", ">NACHHER<"),
        ("update once", "einmal aktualisieren"),
        ("everyone sees the change", "alle sehen die \u00c4nderung"),
        # --- Scene 6: Granular Privacy ---
        ("Granular Privacy", "Granulare Privatsph\u00e4re"),
        (
            "Share work details with colleagues and home addresses with family",
            "Teilen Sie Arbeitsdetails mit Kollegen und Heimadressen mit der Familie",
        ),
        (
            "all from a single identity.",
            "alles \u00fcber eine einzige Identit\u00e4t.",
        ),
        ("Colleague sees", "Kollege sieht"),
        ("Family sees", "Familie sieht"),
        (
            "&#x1F512; address, personal social hidden",
            "&#x1F512; Adresse, persönliche Netzwerke verborgen",
        ),
        ("you control the visibility", "Sie kontrollieren die Sichtbarkeit"),
        # --- Scene 7: Physical Recovery ---
        ("Physical Recovery", "Physische Wiederherstellung"),
        (
            "No master passwords to lose. Regain access through in-person",
            "Keine Master-Passw\u00f6rter zu verlieren. Zugang zur\u00fcckgewinnen durch pers\u00f6nliche",
        ),
        (
            "verification with your trusted inner circle.",
            "Verifizierung mit Ihrem Vertrauenskreis.",
        ),
        ("lost device", "verlorenes Ger\u00e4t"),
        ("trusted circle", "Vertrauenskreis"),
        ("new device", "neues Ger\u00e4t"),
        ("in-person verification", "pers\u00f6nliche Verifizierung"),
        ("no cloud, no passwords", "keine Cloud, keine Passw\u00f6rter"),
        # --- Scene 8: Zero Platform ---
        ("Zero Platform", "Null Plattform"),
        (
            "No feeds, no profiles, no social graphs.",
            "Keine Feeds, keine Profile, keine sozialen Graphen.",
        ),
        (">feeds<", ">Feeds<"),
        (">profiles<", ">Profile<"),
        (">social graph<", ">sozialer Graph<"),
        (
            "Open-source infrastructure you own entirely.",
            "Open-Source-Infrastruktur, die Ihnen vollst\u00e4ndig geh\u00f6rt.",
        ),
        # --- Scene 9: Outro ---
        (
            "Exchange once. Stay connected",
            "Einmal austauschen. Verbunden bleiben",
        ),
        # --- Footer & links ---
        (">Demo (coming soon)<", ">Demo (demn\u00e4chst)<"),
        (">Sponsor<", ">Sponsern<"),
        (">Donate<", ">Spenden<"),
        # --- ARIA labels ---
        ('"How Vauchi works"', '"Wie Vauchi funktioniert"'),
        ('"Toggle dark/light mode"', '"Hell-/Dunkelmodus umschalten"'),
        ('"Choose theme"', '"Thema w\u00e4hlen"'),
        # --- i18n JSON: scene names ---
        ('"Intro"', '"Einleitung"'),
        ('"Exchanged"', '"Ausgetauscht"'),
        ('"Outro"', '"Schluss"'),
        # --- i18n JSON: dynamic text ---
        ('"txt_scanning": "scanning"', '"txt_scanning": "scannt"'),
        ('"txt_paired": "paired"', '"txt_paired": "gekoppelt"'),
        ('"txt_editing": "editing..."', '"txt_editing": "Bearbeitung..."'),
        ('"txt_saved": "\\u2713 saved"', '"txt_saved": "\\u2713 gespeichert"'),
        ('"txt_auto_synced": "\\u2713 auto-synced"', '"txt_auto_synced": "\\u2713 synchronisiert"'),
        ('"txt_waiting": "waiting..."', '"txt_waiting": "wartet..."'),
        ('"txt_restored": "\\u2713 restored"', '"txt_restored": "\\u2713 wiederhergestellt"'),
        ('"txt_new_device": "new device"', '"txt_new_device": "neues Ger\u00e4t"'),
        # --- Contact name ---
        ('class="v-contact-name">You<', 'class="v-contact-name">Sie<'),
        ('class="v-priv-name">You<', 'class="v-priv-name">Sie<'),
    ],
}

IT = {
    "tagline_regex": "Verificabile &#xB7; Crittografia end-to-end &#xB7; Nessun account richiesto",
    "pairs": [
        # --- HTML lang & title ---
        ('<html lang="en">', '<html lang="it">'),
        (
            "<title>Vauchi - Privacy-First Contact Exchange</title>",
            "<title>Vauchi - Scambio di contatti riservato</title>",
        ),
        # --- Scene 0: Intro ---
        (
            "The last time you'll ever exchange contact info.",
            "L\u2019ultima volta che scambierai le tue informazioni di contatto.",
        ),
        (">End-to-End Encrypted<", ">Crittografia end-to-end<"),
        (">No Accounts<", ">Senza account<"),
        # --- Scene 1: Problem ---
        ("The Problem", "Il problema"),
        (
            "Your address book is a graveyard of dead contacts.",
            "La tua rubrica \u00e8 un cimitero di contatti obsoleti.",
        ),
        ("+1 555-0147 (disconnected)", "+1 555-0147 (disconnesso)"),
        ("+44 7911 \u2588\u2588\u2588\u2588 (old number)", "+44 7911 \u2588\u2588\u2588\u2588 (vecchio numero)"),
        ("@jordan.p (deleted)", "@jordan.p (eliminato)"),
        ("sound familiar?", "ti suona familiare?"),
        # --- Scene 2: Exchange ---
        ("Contact Exchange", "Scambio di contatti"),
        (
            "Meet in person. Scan. Connected.",
            "Incontra. Scansiona. Connesso.",
        ),
        ('>YOU<', '>TU<'),
        ('class="v-micro">Show QR<', 'class="v-micro">Mostra QR<'),
        ('class="v-micro">Scan<', 'class="v-micro">Scansiona<'),
        (
            "No phone number or account needed",
            "Nessun numero di telefono o account necessario",
        ),
        # --- Scene 3: Exchanged ---
        (
            "Both phones now hold each other's encrypted contact card.",
            "Entrambi i telefoni ora contengono la scheda contatto crittografata dell\u2019altro.",
        ),
        (">YOUR PHONE<", ">IL TUO TELEFONO<"),
        (">ALEX'S PHONE<", ">TELEFONO DI ALEX<"),
        ("exchange once", "scambia una volta"),
        ("stay connected", "resta connesso"),
        # --- Scene 4: Silent Updates ---
        ("Silent Updates", "Aggiornamenti silenziosi"),
        (
            "When your details change, your friends' phones update",
            "Quando i tuoi dati cambiano, i telefoni dei tuoi amici si aggiornano",
        ),
        (
            "automatically. No notifications, no noise.",
            "automaticamente. Nessuna notifica, nessun rumore.",
        ),
        (">YOU UPDATE<", ">TU AGGIORNI<"),
        (">ALEX SEES<", ">ALEX VEDE<"),
        ("no matter what changes", "qualunque cosa cambi"),
        # --- Scene 5: Platform Freedom ---
        ("Platform Freedom", "Libert\u00e0 di piattaforma"),
        (
            "Switch social networks? Change email providers? Your contacts stay",
            "Cambi social network? Cambi provider e-mail? I tuoi contatti restano",
        ),
        ("              current.\n", "              aggiornati.\n"),
        (">BEFORE<", ">PRIMA<"),
        (">AFTER<", ">DOPO<"),
        ("update once", "aggiorna una volta"),
        ("everyone sees the change", "tutti vedono il cambiamento"),
        # --- Scene 6: Granular Privacy ---
        ("Granular Privacy", "Privacy granulare"),
        (
            "Share work details with colleagues and home addresses with family",
            "Condividi i dettagli lavorativi con i colleghi e gli indirizzi di casa con la famiglia",
        ),
        (
            "all from a single identity.",
            "tutto da un\u2019unica identit\u00e0.",
        ),
        ("Colleague sees", "Il collega vede"),
        ("Family sees", "La famiglia vede"),
        (
            "&#x1F512; address, personal social hidden",
            "&#x1F512; indirizzo, social personali nascosti",
        ),
        ("you control the visibility", "tu controlli la visibilit\u00e0"),
        # --- Scene 7: Physical Recovery ---
        ("Physical Recovery", "Recupero fisico"),
        (
            "No master passwords to lose. Regain access through in-person",
            "Nessuna password principale da perdere. Recupera l\u2019accesso tramite verifica",
        ),
        (
            "verification with your trusted inner circle.",
            "di persona con il tuo cerchio di fiducia.",
        ),
        ("lost device", "dispositivo perso"),
        ("trusted circle", "cerchio di fiducia"),
        ("new device", "nuovo dispositivo"),
        ("in-person verification", "verifica di persona"),
        ("no cloud, no passwords", "nessun cloud, nessuna password"),
        # --- Scene 8: Zero Platform ---
        ("Zero Platform", "Zero piattaforma"),
        (
            "No feeds, no profiles, no social graphs.",
            "Nessun feed, nessun profilo, nessun grafo sociale.",
        ),
        (">feeds<", ">feed<"),
        (">profiles<", ">profili<"),
        (">social graph<", ">grafo sociale<"),
        (
            "Open-source infrastructure you own entirely.",
            "Infrastruttura open source interamente tua.",
        ),
        # --- Scene 9: Outro ---
        (
            "Exchange once. Stay connected",
            "Scambia una volta. Resta connesso",
        ),
        # --- Footer & links ---
        (">Demo (coming soon)<", ">Demo (in arrivo)<"),
        (">Sponsor<", ">Sponsorizza<"),
        (">Donate<", ">Dona<"),
        # --- ARIA labels ---
        ('"How Vauchi works"', '"Come funziona Vauchi"'),
        ('"Toggle dark/light mode"', '"Alterna modalit\u00e0 scuro/chiaro"'),
        ('"Choose theme"', '"Scegli tema"'),
        # --- i18n JSON: scene names ---
        ('"Intro"', '"Introduzione"'),
        ('"Exchanged"', '"Scambiato"'),
        ('"Outro"', '"Conclusione"'),
        # --- i18n JSON: dynamic text ---
        ('"txt_scanning": "scanning"', '"txt_scanning": "scansione"'),
        ('"txt_paired": "paired"', '"txt_paired": "collegato"'),
        ('"txt_editing": "editing..."', '"txt_editing": "modifica..."'),
        ('"txt_saved": "\\u2713 saved"', '"txt_saved": "\\u2713 salvato"'),
        ('"txt_auto_synced": "\\u2713 auto-synced"', '"txt_auto_synced": "\\u2713 sincronizzato"'),
        ('"txt_waiting": "waiting..."', '"txt_waiting": "in attesa..."'),
        ('"txt_restored": "\\u2713 restored"', '"txt_restored": "\\u2713 ripristinato"'),
        ('"txt_new_device": "new device"', '"txt_new_device": "nuovo dispositivo"'),
        # --- Contact name ---
        ('class="v-contact-name">You<', 'class="v-contact-name">Tu<'),
        ('class="v-priv-name">You<', 'class="v-priv-name">Tu<'),
    ],
}

LANG_DATA = {"fr": FR, "de": DE, "it": IT}


def inject_hreflang(html):
    """Add hreflang <link> tags after <meta viewport>."""
    marker = '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
    if marker in html:
        return html.replace(marker, marker + "\n" + HREFLANG_BLOCK)
    return html


def inject_lang_picker(html, active_lang):
    """Add language picker to the footer, before the mode-toggle button."""
    picker = lang_picker_html(active_lang)
    # Insert before the mode/theme controls div
    marker = '<button\n            id="mode-toggle"'
    indent_picker = f"          {picker}\n          "
    if marker in html:
        return html.replace(marker, indent_picker + marker)
    # Fallback: try single-line variant
    marker2 = 'id="mode-toggle"'
    if marker2 in html:
        return html.replace(marker2, f'-->{picker}<!-- ' + marker2, 1)
    print(f"  WARNING: Could not inject language picker for {active_lang}")
    return html


def translate(html, lang_data):
    """Apply all text replacements for a language."""
    result = html
    # Replace tagline (may span lines due to footer whitespace)
    tagline_repl = lang_data["tagline_regex"]
    result = re.sub(TAGLINE_EN, lambda m: tagline_repl, result)
    # Apply ordered pairs
    for old, new in lang_data["pairs"]:
        result = result.replace(old, new)
    return result


def swap_lang_picker_active(html, target_lang):
    """Swap active language in the picker from EN to target_lang.

    Uses regex to handle both single-line and multi-line (formatter-expanded)
    style attributes in the picker links.
    """
    inactive_style = "color: var(--text-secondary); text-decoration: none"
    active_style = (
        "color: var(--accent); text-decoration: none; font-weight: 600"
    )

    # Deactivate EN link (the one with font-weight in its style)
    html = re.sub(
        r'(<a\s+href="/"\s+style=")[^"]*font-weight[^"]*("\s*>EN</a)',
        r"\g<1>" + inactive_style + r"\g<2>",
        html,
    )

    # Activate target language link
    target_href = re.escape(f"/{target_lang}/")
    target_label = re.escape(LANG_LABELS[target_lang])
    html = re.sub(
        r"(<a\s+href=\""
        + target_href
        + r"\"\s+style=\")[^\"]*(\"\s*>"
        + target_label
        + r"</a)",
        r"\g<1>" + active_style + r"\g<2>",
        html,
    )

    return html


def fix_asset_paths(html):
    """Fix relative asset paths for subdirectory pages."""
    return html.replace('src="logo.png"', 'src="/logo.png"')


def main():
    if not os.path.exists(SOURCE_FILE):
        print(f"ERROR: Source file not found: {SOURCE_FILE}")
        sys.exit(1)

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        base_html = f.read()

    # Check if hreflang is already present
    has_hreflang = 'hreflang="en"' in base_html
    has_picker = "font-weight: 600" in base_html or "font-weight:600" in base_html

    # Patch English version with hreflang + language picker
    en_html = base_html
    if not has_hreflang:
        en_html = inject_hreflang(en_html)
    if not has_picker:
        en_html = inject_lang_picker(en_html, "en")
    # Also fix asset path in English for consistency
    en_html = en_html.replace('src="logo.png"', 'src="/logo.png"')

    if en_html != base_html:
        with open(SOURCE_FILE, "w", encoding="utf-8") as f:
            f.write(en_html)
        print(f"  [OK] Patched {SOURCE_FILE} (hreflang + language picker)")
    else:
        print(f"  [OK] {SOURCE_FILE} already up to date")

    # Generate translated versions
    for lang, data in LANG_DATA.items():
        out_dir = os.path.join(PUBLIC_DIR, lang)
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "index.html")

        html = en_html  # Start from patched English
        html = translate(html, data)
        html = fix_asset_paths(html)
        # Update language picker to highlight current language
        html = swap_lang_picker_active(html, lang)

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [OK] Generated {out_file}")

    print(f"\nDone. Generated {len(LANG_DATA)} translations.")


if __name__ == "__main__":
    main()

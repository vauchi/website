// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// Ensures public/app-files/themes/themes.json exists for local testing.
// In CI, build:content produces this. Locally, we copy from ../themes/.

import { existsSync, mkdirSync, copyFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dest = join(__dirname, "..", "public", "app-files", "themes", "themes.json");
const src = join(__dirname, "..", "..", "themes", "themes.json");

if (existsSync(dest)) process.exit(0);

if (!existsSync(src)) {
  console.error("themes/themes.json not found — run from vauchi workspace root");
  process.exit(1);
}

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log("Copied themes.json → public/app-files/themes/themes.json");

# Changelog — GNUVAULT

All notable changes to GNUVAULT. GPL-3.0-or-later. In the highest regard for the
[GNU Project](https://www.gnu.org/) and the [Free Software Foundation](https://www.fsf.org/).

## v0.0.2

- **`rekey` — passphrase rotation.** `GnuVault.rekey()` and `Mausoleum.rekey()`
  rotate a tomb's passphrase in place (fresh salt + nonce), atomically, fail-closed
  on a wrong current passphrase. The plaintext is never written to disk in the clear.
- **`gnuvault` CLI** (`cli.py`) — a standalone command line over a Mausoleum:
  `list · inter · exhume · export · rekey · backup · import · forget · gui · selftest`.
  Passphrases are read with `getpass` (never echoed, never on argv).
- **Test suite** (`test_gnuvault.py`) — runs under pytest or standalone. Verifiability
  is part of transparency: check the claims yourself in seconds.
- Console scripts wired in `pyproject.toml` (`gnuvault`, `gnugui`).

## v0.0.1

- Initial public release at [github.com/gnugui/GNUVAULT](https://github.com/gnugui/GNUVAULT).
- `gnuvault.py` (one tomb — scrypt + AES-256-GCM, `seal`/`open`/`extract_key`),
  `mausoleum.py` (many tombs + `export_key` → sovereign exit, backup to USB),
  `gnugui.py` (the GNUGUI client). Docs, lineage, GPLv3 license.

---

## Releases

GNUVAULT follows the only sensible release schedule for free software:
**the next release ships when ready.** Not on a calendar, not on a quarter — when
it is correct, auditable, and worth your time. *take it, own it, use it, share it.*

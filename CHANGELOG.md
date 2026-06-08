# Changelog — GNUVAULT

All notable changes to GNUVAULT. GPL-3.0-or-later. In the highest regard for the
[GNU Project](https://www.gnu.org/) and the [Free Software Foundation](https://www.fsf.org/).

## v0.0.4

- **AAD bound to tomb identity.** The Mausoleum now seals each tomb with AES-GCM
  associated data derived from the tomb's *name* (`KDF_ID|tomb:<name>`), computed
  at seal AND open and never stored. A sealed file relocated to a different tomb
  name fails closed — closing a cross-tomb/relay gap. Tombs sealed before v0.0.4
  still open (legacy KDF-id AAD fallback) and upgrade to name-binding on `rekey`.
- **Sealed inventory** (`Mausoleum(..., opaque=True)` / `--opaque`). Tombs are
  stored under the SHA-256 of their name, so a directory listing leaks no labels;
  you must know a name to address it.
- `GnuVault.seal_with`/`open_with`/`rekey_with` gain an `aad=` parameter.
- Test suite grows to 12 (AAD binding, opaque inventory, legacy fallback).

## v0.0.3

- **Pluggable Overseer protocol** (`overseer.py`) — *who is allowed to derive the
  key*. Three custodians: `PassphraseOverseer` (default), `KeyfileOverseer`
  (custody by a key file, e.g. on a USB stick), and `WalletSignatureOverseer`
  (key material = `SHA-256(signature)` over a fixed challenge — bring a signature
  from MetaMask/Ledger/any signer; deterministic, never stored).
- `GnuVault.seal_with` / `open_with` / `extract_key_with` / `rekey_with(overseer…)`.
  The passphrase API is now a thin wrapper over these. **`rekey_with` migrates a
  tomb across custody types** (passphrase → wallet signature, etc.) without ever
  exposing the secret.
- **CI** (`.github/workflows/ci.yml`) — selftests + test suite on Python 3.9/3.11/3.12.
- Test suite grows to 9 (keyfile, wallet-signature, cross-custody rekey).

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

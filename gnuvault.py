#!/usr/bin/env python3
# GNUVAULT — a transparent, client-side secret vault.
# Copyright (C) 2026 cypherpunk2048 / BANKON.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details: <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GNUVAULT — the *build your own* example for the cypherpunk2048 Operational
Transparency standard (https://github.com/cypherpunk2048).

Thesis: **open-source security through transparency on the client side.** You
already run the software, so you already hold it — GNUVAULT just gives it to you
from ownership. The whole blackbox is in this one readable file. You can audit
every byte before you trust it with a single secret, change it, and run your
own. This is the Android/Linux model applied to a vault, using GNU tools and the
GPL — the same posture as `Tomb`, the GNU/Linux crypto-undertaker
(https://github.com/dyne/Tomb).

What it does (and nothing it hides):
  • KDF:    scrypt (N=2^15, r=8, p=1) → 32-byte key from passphrase + salt.
  • Cipher: AES-256-GCM (authenticated). Wrong passphrase ⇒ auth failure, not
            garbage plaintext.
  • Sealed bundle: a single JSON envelope {kdf, salt, nonce, ct} — no hidden
            state, no phone-home, no network. Ever.

The blackbox is the vault: your *key* goes into the sealed bundle, your *code*
stays in the open. Two sovereign choices the holder always keeps:
  1. extract_key() — pull the derived key out of the running system. Once
     extracted, the key is yours: portable, off-host, sovereign. No captivity.
  2. build your own — fork this file. It is GPLv3; that right is guaranteed.

Stdlib + `cryptography` (the audited, GNU-friendly primitive set) only.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# scrypt work factors. High enough to be Grover/brute-force-survivable on a
# passphrase; tune up freely — it is your machine and your call.
_SCRYPT_N = 1 << 15   # 32768
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LEN = 32         # AES-256
_SALT_LEN = 16
_NONCE_LEN = 12

CYPHERPUNK2048_STANDARD = "https://github.com/cypherpunk2048"


def _b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def derive_key_material(material: bytes, salt: bytes) -> bytes:
    """scrypt KDF — keying material + salt → 32-byte AES key. Pure, auditable.

    ``material`` is whatever an Overseer produces: a passphrase's bytes, a key
    file, or SHA-256(wallet signature). ``maxmem`` is set explicitly to admit
    the chosen work factor (scrypt needs ~128·N·r bytes; the OpenSSL default cap
    of 32 MiB is below N=2^15). Raising it is a transparent, local decision."""
    return hashlib.scrypt(
        material, salt=salt,
        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEY_LEN,
        maxmem=132 * _SCRYPT_N * _SCRYPT_R + (1 << 20),
    )


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """scrypt KDF from a passphrase (a PassphraseOverseer in one call)."""
    return derive_key_material(passphrase.encode("utf-8"), salt)


@dataclass(frozen=True)
class SealedBundle:
    """The entire on-disk/at-rest representation. No hidden fields."""
    kdf: str
    salt: str       # b64
    nonce: str      # b64
    ct: str         # b64 (ciphertext+GCM tag)

    def to_json(self) -> str:
        return json.dumps({"kdf": self.kdf, "salt": self.salt,
                           "nonce": self.nonce, "ct": self.ct}, indent=2)

    @classmethod
    def from_json(cls, s: str) -> "SealedBundle":
        d = json.loads(s)
        return cls(kdf=d["kdf"], salt=d["salt"], nonce=d["nonce"], ct=d["ct"])


class GnuVault:
    """A transparent vault. The blackbox whose code is open.

    Usage::

        v = GnuVault()
        bundle = v.seal("my secret", "correct horse battery staple")
        # ... store bundle.to_json() anywhere ...
        secret = v.open(SealedBundle.from_json(text), "correct horse battery staple")

    The holder may also ``extract_key(...)`` to take the derived key off-host and
    hold it sovereignly, or fork this GPLv3 file and build their own.
    """

    KDF_ID = f"scrypt(N={_SCRYPT_N},r={_SCRYPT_R},p={_SCRYPT_P})+AES-256-GCM"

    # ── Overseer-based API (passphrase / keyfile / wallet-signature) ──
    def seal_with(self, overseer, secret: str | bytes) -> SealedBundle:
        """Seal ``secret`` under any Overseer's keying material."""
        data = secret.encode("utf-8") if isinstance(secret, str) else secret
        salt = os.urandom(_SALT_LEN)
        nonce = os.urandom(_NONCE_LEN)
        key = derive_key_material(overseer.material(), salt)
        ct = AESGCM(key).encrypt(nonce, data, associated_data=self.KDF_ID.encode())
        return SealedBundle(kdf=self.KDF_ID, salt=_b64e(salt), nonce=_b64e(nonce), ct=_b64e(ct))

    def open_with(self, overseer, bundle: SealedBundle) -> bytes:
        """Open a bundle with an Overseer. Fails closed on the wrong custodian."""
        key = derive_key_material(overseer.material(), _b64d(bundle.salt))
        return AESGCM(key).decrypt(_b64d(bundle.nonce), _b64d(bundle.ct),
                                   associated_data=bundle.kdf.encode())

    def extract_key_with(self, overseer, bundle: SealedBundle) -> bytes:
        """Extract the 32-byte key via an Overseer → sovereign."""
        return derive_key_material(overseer.material(), _b64d(bundle.salt))

    def rekey_with(self, old_overseer, new_overseer, bundle: SealedBundle) -> SealedBundle:
        """Rotate custody: open with the old Overseer, re-seal under the new one
        (fresh salt + nonce). This is how you migrate a tomb from a passphrase to
        a wallet signature, or from one key file to another — without ever
        exposing the secret. Fails closed on the wrong old custodian."""
        secret = self.open_with(old_overseer, bundle)
        return self.seal_with(new_overseer, secret)

    # ── Passphrase API (the common case; thin wrappers over the above) ──
    def seal(self, secret: str | bytes, passphrase: str) -> SealedBundle:
        """Encrypt ``secret`` under ``passphrase``. Returns the full bundle."""
        from overseer import PassphraseOverseer
        return self.seal_with(PassphraseOverseer(passphrase), secret)

    def open(self, bundle: SealedBundle, passphrase: str) -> bytes:
        """Decrypt a bundle. Raises on a wrong passphrase (auth failure)."""
        from overseer import PassphraseOverseer
        return self.open_with(PassphraseOverseer(passphrase), bundle)

    def extract_key(self, bundle: SealedBundle, passphrase: str) -> bytes:
        """Pull the derived 32-byte key OUT of the running system.

        Once you hold these bytes, the key is sovereign: portable, off-host,
        yours. Extraction is a guaranteed exit, not a backdoor."""
        from overseer import PassphraseOverseer
        return self.extract_key_with(PassphraseOverseer(passphrase), bundle)

    def rekey(self, bundle: SealedBundle, old_passphrase: str, new_passphrase: str) -> SealedBundle:
        """Rotate the passphrase: open with the old, re-seal under the new with a
        fresh salt + nonce. Fails closed on a wrong old passphrase."""
        from overseer import PassphraseOverseer
        return self.rekey_with(PassphraseOverseer(old_passphrase),
                               PassphraseOverseer(new_passphrase), bundle)


def _selftest() -> bool:
    v = GnuVault()
    secret = "the key becomes sovereign"
    pw = "correct horse battery staple"
    bundle = v.seal(secret, pw)
    roundtrip = v.open(SealedBundle.from_json(bundle.to_json()), pw).decode()
    assert roundtrip == secret, "roundtrip mismatch"
    # Wrong passphrase must fail closed (auth error), never return plaintext.
    try:
        v.open(bundle, "wrong")
        raise AssertionError("wrong passphrase did not fail")
    except Exception as e:
        if isinstance(e, AssertionError):
            raise
    # Key is extractable → sovereign.
    k = v.extract_key(bundle, pw)
    assert len(k) == _KEY_LEN, "extracted key wrong length"
    print(f"GNUVAULT selftest OK — {v.KDF_ID}; key extractable ({len(k)} bytes); "
          f"standard: {CYPHERPUNK2048_STANDARD}")
    return True


if __name__ == "__main__":
    _selftest()

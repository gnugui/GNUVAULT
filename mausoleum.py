#!/usr/bin/env python3
# GNUVAULT / Mausoleum — a place that holds many tombs.
# Copyright (C) 2026 cypherpunk2048 / BANKON.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.  Distributed WITHOUT ANY WARRANTY.  See <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Mausoleum — multi-tomb management for GNUVAULT.

The Tomb suite, resurrected and made plural: a *Mausoleum* is a directory that
holds many *tombs* (each tomb is one GNUVAULT sealed bundle). It is the standalone
GNU answer to mindX's production **BANKON Vault**, and it deliberately improves
on it where the production version is closed-by-omission:

  • multi-vault by construction — BANKON is one vault per instance; a Mausoleum
    holds as many tombs as you like, each independently keyed.
  • **key export = extraction → sovereignty** — BANKON can rotate *within* the
    vault but has no first-class "give me my key and let me leave"; the
    Mausoleum's `extract_key()`/`export_key()` is exactly that exit. The whole
    point of the cypherpunk2048 standard: you can always walk out with your key.
  • portable + standalone — no FastAPI, no web3, no service. Pure stdlib +
    `cryptography`. Deployable on its own; destined for https://github.com/gnugui.

Lineage it learned from (see LINEAGE.md): BANKON Vault (PBKDF2-600k + HKDF-SHA512
+ AES-256-GCM + atomic rotation), bankoneth (pluggable overseer protocol),
DeltaVerse (AAD-bound sealing), parsec-wallet (Tomb USB cold storage). GNUGUI is
the public-facing client BANKON will ship on top of this.

Security slogans this module keeps in mind:
  • "if you can touch it you own it"
  • "The words computer and security should not be used in the same sentence"
    (note: with no punctuation, the statement stays true)
  • "The only real security is to build your own."
  • take it, own it, use it, share it.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from gnuvault import GnuVault, SealedBundle, CYPHERPUNK2048_STANDARD

SLOGANS = (
    "if you can touch it you own it",
    "The words computer and security should not be used in the same sentence",
    "The only real security is to build your own.",
    "take it, own it, use it, share it.",
)

_TOMB_SUFFIX = ".tomb.json"


@dataclass(frozen=True)
class TombInfo:
    name: str
    path: str
    kdf: str
    bytes: int
    sealed_at: Optional[float]


class Mausoleum:
    """A directory of tombs. Each tomb is an independently-keyed GNUVAULT bundle."""

    def __init__(self, root: str | Path = "~/.gnuvault/mausoleum") -> None:
        self.root = Path(os.path.expanduser(str(root)))
        self.root.mkdir(parents=True, exist_ok=True)
        self._v = GnuVault()

    # ── inventory ──────────────────────────────────────────────────
    def _tomb_path(self, name: str) -> Path:
        safe = "".join(c for c in name if c.isalnum() or c in "-_.").strip(".") or "tomb"
        return self.root / f"{safe}{_TOMB_SUFFIX}"

    def list_tombs(self) -> List[TombInfo]:
        out: List[TombInfo] = []
        for p in sorted(self.root.glob(f"*{_TOMB_SUFFIX}")):
            try:
                meta = json.loads(p.read_text())
            except Exception:
                continue
            out.append(TombInfo(
                name=p.name[: -len(_TOMB_SUFFIX)], path=str(p),
                kdf=meta.get("kdf", "?"), bytes=p.stat().st_size,
                sealed_at=meta.get("_sealed_at"),
            ))
        return out

    # ── inter / exhume (seal / open) ───────────────────────────────
    def inter(self, name: str, secret: str | bytes, passphrase: str) -> TombInfo:
        """Seal ``secret`` into a new tomb named ``name``. Refuses to overwrite."""
        path = self._tomb_path(name)
        if path.exists():
            raise FileExistsError(f"tomb already exists: {path} (forget it first)")
        bundle = self._v.seal(secret, passphrase)
        envelope = json.loads(bundle.to_json())
        envelope["_sealed_at"] = time.time()
        # Atomic write (BANKON discipline): temp + os.replace.
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(envelope, indent=2))
        os.replace(tmp, path)
        return TombInfo(name=name, path=str(path), kdf=bundle.kdf,
                        bytes=path.stat().st_size, sealed_at=envelope["_sealed_at"])

    def exhume(self, name: str, passphrase: str) -> bytes:
        """Open a tomb and return its secret. Wrong passphrase fails closed."""
        return self._v.open(self._load(name), passphrase)

    # ── the exit: extraction → sovereignty ─────────────────────────
    def extract_key(self, name: str, passphrase: str) -> bytes:
        """Pull the 32-byte key OUT of the tomb. Once held, the key is sovereign.
        This is the guaranteed exit the cypherpunk2048 standard requires."""
        return self._v.extract_key(self._load(name), passphrase)

    def export_key(self, name: str, passphrase: str, *, fmt: str = "hex") -> str:
        """Export the extracted key for cold storage / your own build.
        fmt ∈ {hex, base64}. The key leaves the running system, sovereign."""
        import base64
        key = self.extract_key(name, passphrase)
        if fmt == "base64":
            return base64.b64encode(key).decode("ascii")
        return key.hex()

    # ── custody housekeeping ───────────────────────────────────────
    def forget(self, name: str) -> bool:
        """Remove a tomb from the mausoleum (does not shred external copies)."""
        path = self._tomb_path(name)
        if path.exists():
            path.unlink()
            return True
        return False

    def backup(self, dest: str | Path) -> List[str]:
        """Copy every tomb to ``dest`` (e.g. a USB mount — the Tomb cold-storage
        pattern from parsec-wallet). Returns the paths written."""
        dest = Path(os.path.expanduser(str(dest)))
        dest.mkdir(parents=True, exist_ok=True)
        written: List[str] = []
        for p in self.root.glob(f"*{_TOMB_SUFFIX}"):
            target = dest / p.name
            target.write_bytes(p.read_bytes())
            written.append(str(target))
        return written

    def import_tomb(self, path: str | Path) -> TombInfo:
        """Bring an external tomb file into the mausoleum."""
        src = Path(os.path.expanduser(str(path)))
        SealedBundle.from_json(src.read_text())  # validate shape
        name = src.name[: -len(_TOMB_SUFFIX)] if src.name.endswith(_TOMB_SUFFIX) else src.stem
        target = self._tomb_path(name)
        target.write_bytes(src.read_bytes())
        meta = json.loads(target.read_text())
        return TombInfo(name=name, path=str(target), kdf=meta.get("kdf", "?"),
                        bytes=target.stat().st_size, sealed_at=meta.get("_sealed_at"))

    def _load(self, name: str) -> SealedBundle:
        path = self._tomb_path(name)
        if not path.exists():
            raise FileNotFoundError(f"no such tomb: {name}")
        return SealedBundle.from_json(path.read_text())


def _selftest() -> bool:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        m.inter("alpha", "first secret", "pw-alpha")
        m.inter("beta", "second secret", "pw-beta")
        assert {t.name for t in m.list_tombs()} == {"alpha", "beta"}
        assert m.exhume("alpha", "pw-alpha").decode() == "first secret"
        try:
            m.exhume("alpha", "wrong"); raise AssertionError("wrong pw opened tomb")
        except Exception as e:
            if isinstance(e, AssertionError):
                raise
        k = m.export_key("beta", "pw-beta", fmt="hex")
        assert len(k) == 64  # 32 bytes hex
        assert m.forget("alpha") and not m.forget("alpha")
        print(f"Mausoleum selftest OK — multi-tomb + key export (sovereign exit); "
              f"standard: {CYPHERPUNK2048_STANDARD}")
    return True


if __name__ == "__main__":
    _selftest()

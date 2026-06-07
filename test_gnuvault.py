#!/usr/bin/env python3
# GNUVAULT test suite. GPL-3.0-or-later.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Tests for GNUVAULT. Runs under pytest, or standalone (`python3 test_gnuvault.py`).
Operational transparency includes verifiability: you should be able to check the
claims yourself in seconds, without trusting us.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gnuvault import GnuVault, SealedBundle              # noqa: E402
from mausoleum import Mausoleum                          # noqa: E402


def test_seal_open_roundtrip():
    v = GnuVault()
    b = v.seal("hello sovereign", "pw")
    assert v.open(SealedBundle.from_json(b.to_json()), "pw").decode() == "hello sovereign"


def test_wrong_passphrase_fails_closed():
    v = GnuVault()
    b = v.seal("secret", "right")
    try:
        v.open(b, "wrong")
    except Exception:
        return  # expected — authenticated decryption fails, never returns garbage
    raise AssertionError("wrong passphrase did not fail closed")


def test_extract_key_is_32_bytes_and_deterministic():
    v = GnuVault()
    b = v.seal("x", "pw")
    k1 = v.extract_key(b, "pw")
    k2 = v.extract_key(b, "pw")
    assert len(k1) == 32 and k1 == k2          # same bundle + pw → same key (sovereign, reproducible)


def test_rekey_changes_envelope_keeps_secret():
    v = GnuVault()
    b1 = v.seal("constant secret", "old-pw")
    b2 = v.rekey(b1, "old-pw", "new-pw")
    assert v.open(b2, "new-pw").decode() == "constant secret"
    assert b2.salt != b1.salt and b2.ct != b1.ct      # fresh salt + ciphertext
    try:
        v.open(b2, "old-pw"); raise AssertionError("old passphrase still worked after rekey")
    except Exception as e:
        if isinstance(e, AssertionError):
            raise


def test_mausoleum_multi_tomb_and_export():
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        m.inter("a", "secret-a", "pw-a")
        m.inter("b", "secret-b", "pw-b")
        assert {t.name for t in m.list_tombs()} == {"a", "b"}
        assert m.exhume("a", "pw-a").decode() == "secret-a"
        assert len(m.export_key("b", "pw-b")) == 64          # 32 bytes hex
        m.rekey("a", "pw-a", "pw-a2")
        assert m.exhume("a", "pw-a2").decode() == "secret-a"
        assert m.forget("a") and not m.forget("a")


def test_no_overwrite_without_forget():
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        m.inter("dup", "first", "pw")
        try:
            m.inter("dup", "second", "pw"); raise AssertionError("overwrote a tomb")
        except FileExistsError:
            pass


def _run_standalone() -> int:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1; print(f"  FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())

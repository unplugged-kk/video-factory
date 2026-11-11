"""`doctor --require` gates only the named capabilities, so unattended setup does not fail on optional providers."""
import argparse

import pytest

from contentos import cli, providers

CAPS = {"tts": {}, "llm": {}}


def _fake(healthy):
    def candidates(cap, allow_paid=False):
        return [{"id": f"{cap}_p", "tier": "local_oss", "healthy": cap in healthy, "detail": "x"}]

    def select(cap, allow_paid=False):
        c = candidates(cap)[0]
        return (c if c["healthy"] else None), []
    return candidates, select


def _run(monkeypatch, healthy, require):
    monkeypatch.setattr(providers, "load", lambda name: {"capabilities": CAPS})
    monkeypatch.setattr(providers, "candidates", _fake(healthy)[0])
    monkeypatch.setattr(providers, "select", _fake(healthy)[1])
    return cli.cmd_doctor(argparse.Namespace(require=require))


def test_default_fails_when_any_capability_has_no_provider(monkeypatch):
    assert _run(monkeypatch, {"tts"}, None) == 1


def test_require_ignores_capabilities_it_does_not_name(monkeypatch):
    assert _run(monkeypatch, {"tts"}, "tts") == 0


def test_require_still_fails_when_a_named_capability_is_unhealthy(monkeypatch):
    assert _run(monkeypatch, {"tts"}, "tts,llm") == 1


def test_require_rejects_an_unknown_capability_instead_of_passing(monkeypatch, capsys):
    assert _run(monkeypatch, {"tts", "llm"}, "tts,typo") == 2
    assert "typo" in capsys.readouterr().out

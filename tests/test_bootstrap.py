"""Tests for bootstrap installer decisions."""

from subprocess import CompletedProcess

import surfaced.cli.bootstrap as bootstrap


def _install_harness(monkeypatch, installed, failing_commands=None):
    calls = []
    failing_commands = failing_commands or set()

    def fake_cmd_exists(name):
        return name in installed

    def fake_run(cmd, check=True, capture=False):
        calls.append(cmd)
        if cmd in failing_commands:
            return CompletedProcess(cmd, 1, "", "failed")
        if cmd == "curl -fsSL https://claude.ai/install.sh | bash":
            installed.add("claude")
        elif cmd == "curl -fsSL https://bun.sh/install | bash":
            installed.add("bun")
        elif cmd == "bun add --global @openai/codex":
            installed.add("codex")
        elif cmd == "bun add --global @google/gemini-cli":
            installed.add("gemini")
        return CompletedProcess(cmd, 0, "", "")

    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setattr(bootstrap, "_cmd_exists", fake_cmd_exists)
    monkeypatch.setattr(bootstrap, "_run", fake_run)
    return calls


def test_cli_tools_install_bun_before_codex_and_gemini(monkeypatch):
    installed = {"claude"}
    calls = _install_harness(monkeypatch, installed)

    bootstrap._install_cli_tools()

    assert calls == [
        "curl -fsSL https://bun.sh/install | bash",
        "bun add --global @openai/codex",
        "bun add --global @google/gemini-cli",
    ]
    assert {"bun", "codex", "gemini"}.issubset(installed)


def test_cli_tools_use_existing_bun_without_node_fallbacks(monkeypatch):
    installed = {"claude", "bun"}
    calls = _install_harness(monkeypatch, installed)

    bootstrap._install_cli_tools()

    assert calls == [
        "bun add --global @openai/codex",
        "bun add --global @google/gemini-cli",
    ]
    assert not any("npm" in call or "pnpm" in call or "node" in call for call in calls)
    assert not any("brew" in call or "apt-get" in call or "dnf" in call for call in calls)


def test_cli_tools_install_claude_with_native_installer(monkeypatch):
    installed = {"bun", "codex", "gemini"}
    calls = _install_harness(monkeypatch, installed)

    bootstrap._install_cli_tools()

    assert calls == ["curl -fsSL https://claude.ai/install.sh | bash"]
    assert "claude" in installed
    assert not any("@anthropic-ai/claude-code" in call for call in calls)


def test_cli_tools_skip_already_installed_binaries(monkeypatch):
    installed = {"claude", "bun", "codex", "gemini"}
    calls = _install_harness(monkeypatch, installed)

    bootstrap._install_cli_tools()

    assert calls == []


def test_cli_tools_skip_codex_and_gemini_when_bun_unavailable(monkeypatch, capsys):
    installed = {"claude"}
    calls = _install_harness(
        monkeypatch,
        installed,
        failing_commands={"curl -fsSL https://bun.sh/install | bash"},
    )

    bootstrap._install_cli_tools()

    assert calls == ["curl -fsSL https://bun.sh/install | bash"]
    assert "codex" not in installed
    assert "gemini" not in installed
    assert "Skipping codex and gemini because bun is unavailable" in capsys.readouterr().out

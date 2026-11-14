"""Canonical local agent detection shared by the installer front ends.

Detection is strictly read-only: it inspects ``PATH`` lookups, a fixed set
of well-known configuration/application directories, and registered Windows
Harness installations. It never launches, downloads or configures anything.

``AGENT_NAMES`` preserves the adapter-manifest order used by the CLI and the
Python API. Detection reasons use the same English wording as the historical
Bash detector so the front ends can translate them independently:

* ``command: NAME`` -- an executable was found on ``PATH``.
* ``config directory`` -- the agent's well-known configuration directory exists.
* ``config/application directory`` -- configuration *or* application data exists.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# Adapter manifest order; labels match the installer UI wording.
AGENT_NAMES: dict[str, str] = {
    "opencode": "OpenCode",
    "codex": "OpenAI Codex",
    "cursor": "Cursor",
    "pi": "Pi",
    "omp": "OMP",
    "claude": "Claude Code",
    "gemini": "Gemini CLI",
    "copilot": "GitHub Copilot CLI",
    "windsurf": "Windsurf",
    "deepseek-harness": "DeepSeek Harness",
}

COMMAND_REASON = "command: {name}"
CONFIG_REASON = "config directory"
APP_REASON = "config/application directory"


def _home_env(*names: str) -> Path | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return Path(value).expanduser()
    return None


def _windows_harness_installation() -> Path | None:
    """Find a registered Desktop executable without guessing its install drive."""
    try:
        import winreg
    except ImportError:
        return None
    uninstall = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, uninstall, 0, winreg.KEY_READ | view) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root, winreg.EnumKey(root, index)) as entry:
                                name = winreg.QueryValueEx(entry, "DisplayName")[0]
                                if not isinstance(name, str) or not (
                                    name.casefold() == "deepseek harness"
                                    or name.casefold().startswith("deepseek harness ")
                                ):
                                    continue
                                for field in ("InstallLocation", "DisplayIcon"):
                                    try:
                                        value = winreg.QueryValueEx(entry, field)[0]
                                    except OSError:
                                        continue
                                    if not isinstance(value, str) or not value.strip():
                                        continue
                                    if field == "DisplayIcon":
                                        path, separator, suffix = value.rpartition(",")
                                        if separator and suffix.strip().lstrip("+-").isdigit():
                                            value = path
                                    candidate = Path(os.path.expandvars(value.strip().strip('"')))
                                    if field == "InstallLocation":
                                        candidate /= "DeepSeek Harness.exe"
                                    if candidate.name.casefold() == "deepseek harness.exe" and candidate.is_file():
                                        return candidate
                        except OSError:
                            continue
            except OSError:
                continue
    return None


def _detect(id: str, home: Path, project: Path | None) -> str | None:
    """Return a human-readable reason when ``id`` is present, else ``None``."""
    def command(name: str) -> str | None:
        return COMMAND_REASON.format(name=name) if shutil.which(name) else None

    def exists(*candidates: Path | None) -> bool:
        return any(candidate is not None and candidate.is_dir() for candidate in candidates)

    def config_dir(*names: str) -> bool:
        # The project scope additionally inspects the project itself.
        return exists(*([project / name for name in names] if project is not None else []),
                      *(home / name for name in names))

    appdata = _home_env("APPDATA")
    localappdata = _home_env("LOCALAPPDATA")
    mac_support = home / "Library" / "Application Support"

    if id == "opencode":
        if (found := command("opencode")) or config_dir(".config/opencode"):
            return found or CONFIG_REASON
        if project is not None and (project / ".opencode").is_dir():
            return CONFIG_REASON
    elif id == "codex":
        if (found := command("codex")) or config_dir(".codex", ".config/codex"):
            return found or CONFIG_REASON
    elif id == "cursor":
        if found := command("cursor"):
            return found
        if exists(*([project / ".cursor"] if project is not None else []), home / ".cursor", mac_support / "Cursor",
                  None if appdata is None else appdata / "Cursor",
                  None if localappdata is None else localappdata / "Programs" / "cursor"):
            return APP_REASON
    elif id == "pi":
        if (found := command("pi")) or config_dir(".pi"):
            return found or CONFIG_REASON
    elif id == "omp":
        if (found := command("omp")) or config_dir(".omp"):
            return found or CONFIG_REASON
    elif id == "claude":
        if (found := command("claude")) or config_dir(".claude"):
            return found or CONFIG_REASON
    elif id == "gemini":
        if (found := command("gemini")) or config_dir(".gemini"):
            return found or CONFIG_REASON
    elif id == "copilot":
        if (found := command("copilot")) or (fallback := command("github-copilot-cli")) or config_dir(".copilot"):
            return found or fallback or CONFIG_REASON
    elif id == "windsurf":
        if found := command("windsurf"):
            return found
        if exists(*([project / ".windsurf"] if project is not None else []), home / ".codeium" / "windsurf",
                  mac_support / "Windsurf", None if appdata is None else appdata / "Windsurf",
                  None if localappdata is None else localappdata / "Programs" / "Windsurf"):
            return APP_REASON
    elif id == "deepseek-harness":
        if (found := command("dsh")) or command("deepseek-harness"):
            return found or COMMAND_REASON.format(name="deepseek-harness")
        dsh_home = _home_env("DSH_HOME")
        if config_dir(".dsh", ".deepseek-harness") or exists(dsh_home):
            return CONFIG_REASON
        executable = _windows_harness_installation()
        if executable is not None:
            return f"registered application: {executable.parent}"
    return None


def detect_agents(home: Path, *, project: Path | None = None) -> dict[str, str]:
    """Return ``{agent id: reason}`` for locally present agents, manifest order.

    ``home`` is the user directory that the installer targets (``Path.home()``),
    not necessarily a Git-Bash style ``HOME``. ``project`` adds project-local
    configuration lookups and MUST stay ``None`` for global detection.
    """
    detected: dict[str, str] = {}
    for id in AGENT_NAMES:
        reason = _detect(id, home, project)
        if reason is not None:
            detected[id] = reason
    return detected

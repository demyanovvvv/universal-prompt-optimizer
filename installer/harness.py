"""DeepSeek Harness (Cordis) native bundle contract and profile-manifest edits.

Two surfaces are defined here and nowhere else:

* the installer-owned native package deployed under ``<root>/.dsh/plugins`` and,
  for a global automatic install, mirrored into the Desktop profile's
  ``node_modules`` so the native manager can load and reinstall it offline;
* the Desktop profile manifest (``<root>/.dsh/profiles/desktop/package.json``)
  dependency entry and bundle selection.

The profile manifest is never part of the installation inventory: only the
``universal-prompt-optimizer`` dependency key, the ``node_modules`` payload and
the transient package-local lock are owned. Every other dependency, ``dsh``
field, bundle entry and patch file belongs to the user.

Manifest edits reuse the host protocol: the sibling ``package.json.lock`` is
created exclusively with ``'<pid>\\n'`` for the whole execution transaction, so a
running Harness never observes a half-written manifest. Contention fails clearly
instead of retrying. The edits are pure string transforms, so planning compares
text and never writes.
"""

from __future__ import annotations

import json
from pathlib import Path

from .domain import Operation
from .filesystem import atomic_write_bytes
import os
from .transaction import InstallTransaction

BUNDLE_NAME = "universal-prompt-optimizer"
BUNDLE_ID = BUNDLE_NAME
# Relative to the Desktop profile directory: the payload lives in the installer
# owned ``<root>/.dsh/plugins`` tree, so a native reinstall needs no network.
DEPENDENCY_SPEC = "file:../../plugins/prompt-optimizer"
PLUGIN_PACKAGE = "package.json"
PROFILE_DIRECTORY = ".dsh/profiles/desktop"
PROFILE_NAME = "dsh-profile-desktop"
PLUGIN_DIRECTORY = ".dsh/plugins/prompt-optimizer"
MANIFEST_LOCK_NAME = "package.json.lock"
MANIFEST_PARAMS = {"name": BUNDLE_NAME, "spec": DEPENDENCY_SPEC}
PROJECT_OVERLAY = ".dsh/prompt-optimizer.patch.yml"
# Verified Desktop defaults, so a profile created before the first launch still
# composes the base and web-app bundles the application expects.
DEFAULT_BUNDLES = ("@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app")
MANIFEST_KINDS = frozenset({"merge_dsh_manifest", "delete_dsh_manifest"})


def plugin_package_path(root: Path) -> Path:
    return root / PLUGIN_DIRECTORY


def plugin_skill_path(root: Path) -> Path:
    return root / PLUGIN_DIRECTORY / "skills" / "prompt-optimizer"


def dsh_home(root: Path) -> Path:
    """Optimizer installations stay under the selected home, independent of DSH_HOME."""
    return root / ".dsh"


def profile_directory(root: Path) -> Path:
    return dsh_home(root) / "profiles" / "desktop"


def manifest_path(root: Path) -> Path:
    return profile_directory(root) / PLUGIN_PACKAGE


def manifest_lock_path(root: Path) -> Path:
    return profile_directory(root) / MANIFEST_LOCK_NAME


def profile_payload_path(root: Path) -> Path:
    return profile_directory(root) / "node_modules" / BUNDLE_NAME


def project_overlay_path(root: Path) -> Path:
    return root / PROJECT_OVERLAY


def lock_path_for(manifest: Path) -> Path:
    return manifest.with_name(MANIFEST_LOCK_NAME)


def manifest_locks(plan) -> tuple[Path, ...]:
    """Return the package lock file guarding every manifest edit in a plan."""
    paths = {lock_path_for(operation.path) for operation in plan.operations
             if operation.kind in MANIFEST_KINDS}
    return tuple(sorted(paths))


def native_activation_hint(root: Path) -> str:
    """Activation text for the native Desktop bundle."""
    return (
        f"DeepSeek Harness plugin and skill installed as native bundle {BUNDLE_NAME}. "
        f"The installer registers its local package without running a package manager; "
        f"existing profile preferences and user patches are preserved. Open Plugins "
        f"or restart Desktop if the bundle list does not refresh."
    )


def project_activation_hint(command: str) -> str:
    """Activation text for a project install: loading stays explicit through the overlay."""
    return (
        f"DeepSeek Harness plugin and skill installed. To activate after installation: {command} "
        f"(place --patch before the app arguments; project installs are never auto-registered). "
        f"The installer never edits your Harness profile, cordis.patch.yml or package manifests."
    )


def reject_symlink(path: Path) -> None:
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise ValueError(f"refusing to write through symlink: {current}")
        current = current.parent


def load_manifest(text: str | None, path: Path) -> dict:
    if text is None:
        return {}
    if not text.strip():
        raise ValueError(f"invalid DeepSeek Harness profile manifest: {path}")
    try:
        value = json.loads(text)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid DeepSeek Harness profile manifest: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"DeepSeek Harness profile manifest root must be an object: {path}")
    return value


def _profile_of(manifest: dict, path: Path, *, create: bool) -> dict | None:
    dsh = manifest.get("dsh")
    if dsh is None:
        if not create:
            return None
        dsh = manifest["dsh"] = {}
    if not isinstance(dsh, dict):
        raise ValueError(f"dsh must be an object: {path}")
    profile = dsh.get("profile")
    if profile is None:
        if not create:
            return None
        profile = dsh["profile"] = {}
    if not isinstance(profile, dict):
        raise ValueError(f"dsh.profile must be an object: {path}")
    return profile


def selection_state(text: str | None, path: Path) -> str:
    """Classify a manifest: ``absent``, ``enabled`` or ``disabled`` (selection dropped)."""
    if text is None or not text.strip():
        return "absent"
    manifest = load_manifest(text, path)
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, dict) or BUNDLE_NAME not in dependencies:
        return "absent"
    profile = _profile_of(manifest, path, create=False)
    bundles = profile.get("bundles") if isinstance(profile, dict) else None
    return "enabled" if isinstance(bundles, list) and BUNDLE_ID in bundles else "disabled"


def merge_manifest(text: str | None, path: Path) -> str | None:
    """Register the local bundle while preserving all existing profile data."""
    if text is None:
        manifest = {
            "name": PROFILE_NAME,
            "private": True,
            "dependencies": {},
            "dsh": {"profile": {"bundles": list(DEFAULT_BUNDLES)}},
        }
    else:
        manifest = load_manifest(text, path)
        if not manifest:
            raise ValueError(f"invalid DeepSeek Harness profile manifest: {path}")
    if manifest.get("name") not in (None, PROFILE_NAME):
        raise ValueError(f"refusing to register a bundle in a foreign profile manifest: {path}")
    dependencies = manifest.get("dependencies")
    if dependencies is None:
        dependencies = manifest["dependencies"] = {}
    if not isinstance(dependencies, dict):
        raise ValueError(f"dependencies must be an object: {path}")
    if BUNDLE_NAME in dependencies:
        recorded = dependencies[BUNDLE_NAME]
        if recorded != DEPENDENCY_SPEC:
            raise ValueError(f"refusing to replace the existing {BUNDLE_NAME} dependency {recorded!r}: {path}")
        return None
    profile = _profile_of(manifest, path, create=True)
    if profile is None:
        raise ValueError(f"dsh.profile must be an object: {path}")
    bundles = profile.get("bundles")
    if bundles is None:
        bundles = profile["bundles"] = list(DEFAULT_BUNDLES)
    if not isinstance(bundles, list) or any(not isinstance(item, str) for item in bundles):
        raise ValueError(f"dsh.profile.bundles must be an array of strings: {path}")
    dependencies[BUNDLE_NAME] = DEPENDENCY_SPEC
    if BUNDLE_ID not in bundles and "!" + BUNDLE_ID not in bundles:
        bundles.append(BUNDLE_ID)
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def remove_manifest(text: str | None, path: Path) -> str | None:
    """Remove only our exact local dependency and its bundle selection."""
    if text is None:
        return None
    manifest = load_manifest(text, path)
    dependencies = manifest.get("dependencies")
    if dependencies is not None and not isinstance(dependencies, dict):
        return None
    if isinstance(dependencies, dict):
        if BUNDLE_NAME in dependencies and dependencies[BUNDLE_NAME] != DEPENDENCY_SPEC:
            return None
        dependencies.pop(BUNDLE_NAME, None)
        if not dependencies:
            manifest.pop("dependencies", None)
    profile = _profile_of(manifest, path, create=False)
    if isinstance(profile, dict):
        bundles = profile.get("bundles")
        if isinstance(bundles, list):
            profile["bundles"] = [item for item in bundles
                                  if item not in (BUNDLE_ID, "!" + BUNDLE_ID)]
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def require_manifest(root: Path) -> None:
    """Refuse a malformed or foreign profile manifest before any write happens."""
    path = manifest_path(root)
    reject_symlink(path)
    if not path.exists():
        return
    if not path.is_file():
        raise ValueError(f"profile manifest is not a file: {path}")
    manifest = load_manifest(path.read_text(encoding="utf-8"), path)
    if manifest.get("name") not in (None, PROFILE_NAME):
        raise ValueError(f"refusing to use a foreign profile manifest: {path}")
    dependencies = manifest.get("dependencies")
    if dependencies is not None and not isinstance(dependencies, dict):
        raise ValueError(f"dependencies must be an object: {path}")
    if isinstance(dependencies, dict) and BUNDLE_NAME in dependencies:
        recorded = dependencies[BUNDLE_NAME]
        if not isinstance(recorded, str):
            raise ValueError(f"invalid {BUNDLE_NAME} dependency: {path}")

def require_profile_manifest(root: Path) -> None:
    """Validate an existing Desktop profile without mutating it."""
    path = manifest_path(root)
    if not path.exists():
        return
    manifest = load_manifest(path.read_text(encoding="utf-8"), path)
    profile = _profile_of(manifest, path, create=False)
    if profile is None:
        return
    bundles = profile.get("bundles")
    if bundles is not None and (not isinstance(bundles, list)
                                or any(not isinstance(item, str) for item in bundles)):
        raise ValueError(f"dsh.profile.bundles must be an array of strings: {path}")


def require_native_package(package: Path, *, allow_legacy: bool = False) -> None:
    """Refuse unowned destinations; optionally admit the tracked v5.15 legacy file."""
    reject_symlink(package)
    if not package.exists():
        if package.parent.exists():
            if (allow_legacy and package.parent.is_dir()
                    and {item.name for item in package.parent.iterdir()} == {"index.mjs"}
                    and (package.parent / "index.mjs").is_file()
                    and not (package.parent / "index.mjs").is_symlink()):
                return
            raise ValueError(f"native package manifest is missing from existing destination: {package}")
        return
    if not package.is_file():
        raise ValueError(f"native package manifest is not a file: {package}")
    try:
        value = json.loads(package.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid native package manifest: {package}") from exc
    if not isinstance(value, dict) or value.get("name") != BUNDLE_NAME:
        name = value.get("name") if isinstance(value, dict) else None
        raise ValueError(f"native package at {package} is not {BUNDLE_NAME}: {name!r}")


def validate_payload(source: Path, destination: Path, *, allow_legacy: bool = False) -> None:
    """Refuse an unowned, colliding or symlinked native package destination."""
    reject_symlink(destination)
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"native package destination is not a directory: {destination}")
    if source.name == "plugin":
        if not (source / PLUGIN_PACKAGE).is_file():
            raise ValueError(f"native package source has no {PLUGIN_PACKAGE}: {source}")
        require_native_package(destination / PLUGIN_PACKAGE, allow_legacy=allow_legacy)


def release_lock(path: Path) -> None:
    """Drop the native package lock; missing is success."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def apply_merge(operation: Operation, transaction: InstallTransaction) -> None:
    path = operation.path
    text = path.read_text(encoding="utf-8") if path.exists() else None
    merged = merge_manifest(text, path)
    if merged is None:
        return
    transaction.record(path)
    transaction.mkdir(path.parent)
    atomic_write_bytes(path, merged.encode("utf-8"))


def apply_delete(operation: Operation, transaction: InstallTransaction) -> None:
    path = operation.path
    if not path.exists() or not path.is_file():
        return
    removed = remove_manifest(path.read_text(encoding="utf-8"), path)
    if removed is None:
        return
    transaction.record(path)
    transaction.mkdir(path.parent)
    atomic_write_bytes(path, removed.encode("utf-8"))


def plan_manifest_merge(root: Path) -> Operation:
    return Operation("merge_dsh_manifest", manifest_path(root),
                     content=json.dumps(MANIFEST_PARAMS).encode("utf-8"),
                     label="DeepSeek Harness native bundle registration")


def plan_manifest_delete(root: Path) -> Operation:
    return Operation("delete_dsh_manifest", manifest_path(root),
                     content=json.dumps(MANIFEST_PARAMS).encode("utf-8"),
                     label="DeepSeek Harness native bundle registration")
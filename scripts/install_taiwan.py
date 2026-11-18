#!/usr/bin/env python3
"""Install this checkout's Taiwan Codex skills, retaining prior symlink targets."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def install(destination):
    destination = Path(destination).expanduser().absolute()
    names = sorted([*json.loads((ROOT / "TAIWAN_SKILL_MAP.json").read_text())["active"], "trading-skills-navigator"])
    if len(names) != len(set(names)) or any(not isinstance(n, str) or not n or Path(n).name != n or n in (".", "..") for n in names):
        raise ValueError("Invalid skill index")
    previous = {}
    for name in names:
        source, target = ROOT / "skills" / name, destination / name
        if not (source / "SKILL.md").is_file():
            raise ValueError("Missing skill source")
        if target.exists() and not target.is_symlink():
            raise ValueError(f"Refusing to replace non-symlink skill: {name}")
        previous[name] = os.readlink(target) if target.is_symlink() else None
    destination.mkdir(parents=True, exist_ok=True)
    backup_dir = destination.parent / "skill-install-backups"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / ("taiwan-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    backup.write_text(json.dumps({"destination": str(destination), "previous": previous}, indent=2) + "\n")
    updated = []
    try:
        for name in names:
            target = destination / name
            temp = destination / ("." + name + ".taiwan-install")
            if temp.exists() or temp.is_symlink():
                raise ValueError("Installation temporary path already exists")
            updated.append(name)
            try:
                temp.symlink_to(ROOT / "skills" / name, target_is_directory=True)
                os.replace(temp, target)
            finally:
                if temp.is_symlink():
                    temp.unlink()
    except BaseException:
        for name in reversed(updated):
            target = destination / name
            target.unlink(missing_ok=True)
            if previous[name] is not None:
                target.symlink_to(previous[name], target_is_directory=True)
        raise
    return {"installed": len(names), "source": str(ROOT), "backup": str(backup)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path,
                        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.skills_dir), ensure_ascii=False))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

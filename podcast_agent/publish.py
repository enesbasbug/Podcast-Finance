"""Step 4: upload the MP3 as a GitHub Release asset (free, public, stable URL)."""

import subprocess
from pathlib import Path

from . import config


def release_exists(tag: str) -> bool:
    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", config.GITHUB_REPOSITORY], capture_output=True, text=True
    )
    return result.returncode == 0


def upload_release(tag: str, title: str, notes: str, mp3: Path) -> str:
    """Create (or replace the asset on) release `tag`; return the public download URL."""
    if release_exists(tag):
        subprocess.run(
            ["gh", "release", "upload", tag, str(mp3), "--clobber", "--repo", config.GITHUB_REPOSITORY], check=True
        )
    else:
        subprocess.run(
            [
                "gh", "release", "create", tag, str(mp3),
                "--repo", config.GITHUB_REPOSITORY,
                "--title", title,
                "--notes", notes,
                "--latest=false",
            ],
            check=True,
        )
    return f"https://github.com/{config.GITHUB_REPOSITORY}/releases/download/{tag}/{mp3.name}"

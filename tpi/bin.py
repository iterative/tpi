"""Download & cache terraform binaries"""
import logging
import platform
import re
from functools import partial
from os import PathLike
from pathlib import Path
from typing import Union

from miutil.fdio import extractall
from miutil.web import urlopen_cached

__all__ = ["ARCH", "CACHE_DIR", "OS", "VERSION_TF", "terraform"]
log = logging.getLogger(__name__)

CACHE_DIR = "~/.terraform"
VERSION_TF = "1.0.5"
ARCH = "amd64" if "64" in platform.machine() else "386"
match = partial(re.match, string=platform.system(), flags=re.I)
for i in {"darwin", "freebsd", "linux", "openbsd", "windows|cli|cygwin|msys"}:
    if match(i):
        OS = i.split("|", 1)[0]
        break
else:
    OS = match("[a-zA-Z]+").group(0).lower()
AnyPath = Union[str, "PathLike[str]", Path]


def terraform(cache: AnyPath = CACHE_DIR, version: str = VERSION_TF) -> Path:
    cache = Path(cache).expanduser()
    bin = cache / ("terraform" + (".exe" if OS == "windows" else ""))
    url = (
        f"https://releases.hashicorp.com/terraform"
        f"/{version}/terraform_{version}_{OS}_{ARCH}.zip"
    )
    if not bin.is_file():
        log.info("Downloading to %s", cache)
        with urlopen_cached(url, cache) as fd:
            extractall(fd, cache)
    assert bin.is_file()
    if OS != "windows":
        bin.chmod(0o755)
    return bin

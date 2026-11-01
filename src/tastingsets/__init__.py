import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("tastingsets")
except PackageNotFoundError:
    try:
        _pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with _pyproject.open("rb") as _f:
            __version__ = tomllib.load(_f)["project"]["version"]
    except (OSError, KeyError):
        __version__ = "unknown"
from importlib.metadata import PackageNotFoundError, metadata, version

# The version is derived from Git tags at build/install time (hatch-vcs).
# Without an installed package there is no metadata.
try:
    __version__ = version("tastingsets")
    _project_urls = metadata("tastingsets").get_all("Project-URL") or []
except PackageNotFoundError:
    __version__ = "unknown"
    _project_urls = []

# Project URL from [project.urls] in pyproject.toml ("Repository"); empty if unavailable.
__url__ = next(
    (
        entry.partition(",")[2].strip()
        for entry in _project_urls
        if entry.partition(",")[0].strip().lower() == "repository"
    ),
    "",
)

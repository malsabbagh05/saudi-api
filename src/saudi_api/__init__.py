"""saudi-api: an open, bilingual catalogue of Saudi APIs for developers and AI agents."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("saudi-api")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"

PROJECT_URL = "https://github.com/malsabbagh05/saudi-api"

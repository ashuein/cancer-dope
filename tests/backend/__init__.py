"""Backend test package.

Extends the package path so pytest can import application modules under
``backend`` even when this test package is imported first.
"""

from pathlib import Path

APP_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(APP_BACKEND) not in __path__:
    __path__.append(str(APP_BACKEND))

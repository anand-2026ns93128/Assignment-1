"""Allow ``python -m reminder_agent``."""

import sys

from .cli import main

sys.exit(main())

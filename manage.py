#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

from core.locale_setup import set_brazilian_locale


def main():
    """Run administrative tasks."""
    set_brazilian_locale()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import (  # pylint: disable=import-outside-toplevel
            execute_from_command_line,
        )
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

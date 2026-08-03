#!/usr/bin/env python
"""Django buyruq qatori yordamchisi."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Django import qilinmadi. Virtual muhit faollashtirilganmi va "
            "bog'liqliklar o'rnatilganmi?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

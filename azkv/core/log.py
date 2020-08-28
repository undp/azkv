# -*- coding: utf-8 -*-
"""Log handler module."""
from cement.ext.ext_colorlog import ColorLogHandler


class AzKVLogHandler(ColorLogHandler):
    """Class implementing log handler with custom format.

    This class is a sub-class of :class:`cement.ext.ext_colorlog.ColorLogHandler`,
    and it changes log format for console and file outputs.

    """

    class Meta:
        """Handler meta-data."""

        label = "colorlog_custom_format"

        config_section = "log.colorlog"

        console_format = "%(asctime)-15s %(levelname)-8s %(namespace)s : %(message)s"

"""Base app controller module."""
from cement import Controller
from cement.utils.version import get_version_banner

from ..core.version import get_version

VERSION_BANNER = """
AzKV %s
%s
""" % (
    get_version(),
    get_version_banner(),
)


class Base(Controller):
    """ Class implementing base app controller."""

    class Meta:
        """Controller meta-data."""

        label = "base"

        description = "CLI client for the Azure Key Vault data plane."
        epilog = "Usage: azkv secrets search <secret_name>"

        arguments = [
            # add a version banner
            (["-v", "--version"], {"action": "version", "version": VERSION_BANNER}),
        ]

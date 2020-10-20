"""Main app module."""
from cement import App, TestApp, init_defaults
from cement.core.exc import CaughtSignal

from .controllers.base import Base
from .controllers.keyvaults import Keyvaults
from .controllers.secrets import Secrets
from .core.exc import AzKVError
from .core.hooks import extend_vault_creds, log_app_version
from .core.log import AzKVLogHandler

# configuration defaults
CONFIG = init_defaults("azkv", "azkv.credentials", "azkv.keyvaults")
CONFIG["azkv"]["credentials"] = {"type": "EnvironmentVariables"}
CONFIG["azkv"]["keyvaults"] = []


class AzKV(App):
    """AzKV primary application."""

    class Meta:
        """Application meta-data."""

        label = "azkv"

        # configuration defaults
        config_defaults = CONFIG

        # call sys.exit() on close
        exit_on_close = True

        # register functions to hooks
        hooks = [
            ("post_setup", log_app_version),
            ("post_setup", extend_vault_creds),
        ]

        # load additional framework extensions
        extensions = [
            "colorlog",
            "jinja2",
            "yaml",
        ]

        # configuration handler
        config_handler = "yaml"

        # configuration file suffix
        config_file_suffix = ".yaml"

        # set log handler
        log_handler = "colorlog_custom_format"

        # set the output handler
        output_handler = "jinja2"

        # register handlers
        handlers = [Base, AzKVLogHandler, Keyvaults, Secrets]


class AzKVTest(TestApp, AzKV):
    """A sub-class of AzKV that is better suited for testing."""

    class Meta:
        """Test application meta-data."""

        label = "azkv"


def main():
    """App entry point."""
    with AzKV() as app:
        try:
            app.run()

        except AssertionError as e:
            print("AssertionError > %s" % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback

                traceback.print_exc()

        except AzKVError as e:
            print("AzKVError > %s" % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback

                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print("\n%s" % e)
            app.exit_code = 0


if __name__ == "__main__":
    main()

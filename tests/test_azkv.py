"""Module defines app test cases."""
from azkv.main import AzKVTest


def test_azkv():
    """Test azkv without any subcommands or arguments."""
    with AzKVTest() as app:
        app.run()
        assert app.exit_code == 0  # noqa: S101


def test_azkv_debug():
    """Test that debug mode is functional."""
    argv = ["--debug"]
    with AzKVTest(argv=argv) as app:
        app.run()
        assert app.debug is True  # noqa: S101

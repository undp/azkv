"""Keyvaults controller module."""
from typing import Any, Dict, List

from cement import Controller, ex


class Keyvaults(Controller):
    """ Class implementing controller for ``keyvaults`` namespace."""

    class Meta:
        """Controller meta-data."""

        label: str = "keyvaults"
        stacked_on: str = "base"
        stacked_type: str = "nested"
        help: str = "Operations with key vaults"  # noqa: A003

    @ex(help="list all Azure Key Vaults in use by the app")
    def show(self) -> None:
        """List all Key Vaults from config."""
        # get keyvaults and their short names from config
        keyvaults: Dict[str, Any] = self.app.config.get("azkv", "keyvaults")

        output_data: Dict[str, List[Any]] = {"keyvaults": []}

        for vault in keyvaults.keys():
            output_data["keyvaults"].append(
                {"name": vault, "url": keyvaults[vault]["url"]}
            )

        self.app.render(output_data, "keyvaults_list.j2")

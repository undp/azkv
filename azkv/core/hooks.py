# -*- coding: utf-8 -*-
"""Framework hooks module."""
from typing import Any, Dict, Optional, Union

from azure.identity import (
    EnvironmentCredential,
    ManagedIdentityCredential,
)

from cement import App

from .version import get_version


def log_app_version(app: App) -> None:
    """Log the version of the app.

    Parameters
    ----------
    app
        Cement Framework application object.
    """
    app.log.info("AzKV version {}".format(get_version()))  # noqa: G001


def extend_vault_creds(app: App) -> None:
    """Extend app with azure credentials for each vault.

    Obtains Azure identity either from Environment Variables or Managed Identity.

    Parameters
    ----------
    app
        Cement Framework application object.
    """
    app.log.info("Extending app object with Azure Key Vault credentials")

    common_creds_config: Dict[str, str] = app.config.get("azkv", "credentials")
    if common_creds_config:
        common_type: Optional[str] = common_creds_config.get("type")
        common_client_id: Optional[str] = common_creds_config.get("client_id")
    else:
        common_type = "EnvironmentVariables"
        common_client_id = None

    keyvaults: Dict[str, Any] = app.config.get("azkv", "keyvaults")

    vault_creds: Dict[str, Union[EnvironmentCredential, ManagedIdentityCredential]] = {}

    creds_from_env = EnvironmentCredential()
    creds_from_mi = ManagedIdentityCredential()

    for vault, config in keyvaults.items():
        creds_config = config.get("credentials", None)

        if creds_config:
            creds_type = creds_config.get("type", common_type)
            creds_client_id = creds_config.get("client_id", common_client_id)
        else:
            creds_type = common_type
            creds_client_id = common_client_id

        app.log.info(
            "Vault '{}' would be queried with credentials from '{}'".format(  # noqa: G001, E501
                vault, creds_type
            )
        )

        if creds_type == "EnvironmentVariables":
            vault_creds[vault] = creds_from_env

        elif creds_type == "SystemManagedIdentity":
            vault_creds[vault] = creds_from_mi

        elif creds_type == "UserManagedIdentity":
            vault_creds[vault] = ManagedIdentityCredential(client_id=creds_client_id)

            app.log.info("  client_id={}".format(creds_client_id))  # noqa: G001

            if creds_client_id is None:
                app.log.warning(
                    "  no 'client_id' defied, changed to credentials from SystemManagedIdentity"  # noqa: E501
                )

        else:
            # fmt: off
            app.log.warning(
                "Unknown value '{}' in credentials type, assume 'EnvironmentVariables'".format(creds_type)  # noqa: G001, E501
            )
            # fmt: on

            vault_creds[vault] = creds_from_env

    app.extend("vault_creds", vault_creds)

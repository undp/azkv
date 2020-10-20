"""Secrets controller module."""
from base64 import standard_b64decode
from binascii import Error as BinAsciiError
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, KeysView, List, Optional

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.keyvault.secrets import KeyVaultSecret, SecretClient

from cement import Controller, ex
from cement.utils import shell

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate


class Secrets(Controller):
    """ Class implementing controller for ``secrets`` namespace."""

    class Meta:
        """Controller meta-data."""

        label: str = "secrets"
        stacked_on: str = "base"
        stacked_type: str = "nested"
        help: str = "Operations with secrets"  # noqa: A003

    def _get_secret(
        self, vault: str, name: str, version: str = None,
    ) -> Optional[KeyVaultSecret]:
        """Get a secret from the specific Azure Key Vault.

        Fetches secret from ``vault`` with the specified ``name`` and ``version``.

        Parameters
        ----------
        vault
            Short name of the Key Vault form config file.

        name
            The name of the secret.

        version
            (optional) Version of the secret to get. If unspecified, gets
            the latest version.

        Returns
        -------
        :obj:`~typing.Optional` [:obj:`~azure.keyvault.secrets.KeyVaultSecret`]
            If found, all of a secret’s properties, and its value. Otherwise returns
            ``None``.

        """
        keyvaults: Dict[str, Any] = self.app.config.get("azkv", "keyvaults")

        self.app.log.info(
            "Querying vault '{}' through '{}'".format(vault, keyvaults[vault]["url"])
        )
        try:
            with SecretClient(
                vault_url=keyvaults[vault]["url"],
                credential=self.app.vault_creds[vault],
            ) as secret_client:
                return secret_client.get_secret(name, version)
        except ResourceNotFoundError:
            self.app.log.info("Secret '{}' not found in vault '{}'".format(name, vault))
        except ClientAuthenticationError as e:
            self.app.log.error("ClientAuthenticationError: {}".format(str(e)))
        except HttpResponseError as e:
            self.app.log.error("HttpResponseError: {}".format(str(e)))
        except ServiceRequestError as e:
            self.app.log.error("ServiceRequestError: {}".format(str(e)))
        else:
            return None

    def _get_vaults(self, param_name: str = "undefined") -> List[str]:
        """Get the list of applicable Azure Key Vaults.

        Expects a CLI option within ``pargs`` named ``param_name`` which accumulates
        a list of scoped vaults. If such parameter does not exist or is empty,
        returns the full list of configured Azure Key Vaults.

        Parameters
        ----------
        param_name
            Name of the ``pargs`` property containing corresponding CLI
            parameter with the list of vault names.

        Returns
        -------
        List[str]
            List of Azure Key Vault names scoped through CLI or config.

        """
        # get key vaults from config
        keyvaults: Dict[str, Any] = self.app.config.get("azkv", "keyvaults")
        # get key vault short names from config
        keyvault_names: KeysView[str] = keyvaults.keys()

        vault_list: List[str] = []

        # check if expected CLI parameter is present and get corresponding value
        try:
            vault_param = getattr(self.app.pargs, param_name)
        except AttributeError:
            self.app.log.error("CLI parameter '{}' does not exist".format(param_name))
        else:
            # get list of scoped vault names, if specified
            if vault_param is not None:
                dirty_vault_list = vault_param

                # verify that provided vault names exist in config
                for vault in dirty_vault_list:
                    if vault not in keyvault_names:
                        self.app.log.error("Unknown Key Vault '{}'".format(vault))
                    else:
                        vault_list.append(vault)

            # otherwise, use all available vault names
            else:
                vault_list = list(keyvault_names)

        return vault_list

    @ex(
        help="download secret from first available Azure Key Vault",
        arguments=[
            (
                ["--name", "-n"],
                {
                    "help": "name of the secret",
                    "action": "store",
                    "metavar": "SECRET_NAME",
                    "required": True,
                    "dest": "secret_name",
                },
            ),
            (
                ["--file", "-f"],
                {
                    "help": "File path to save the secret \
                        (ensures file mode is '0600')",
                    "action": "store",
                    "metavar": "PATH",
                    "required": True,
                    "dest": "file_path_secret",
                },
            ),
            (
                ["--b64decode", "-b64"],
                {
                    "help": "Apply Base64 decoding to the secret before saving",
                    "action": "store_true",
                    "dest": "b64decode",
                },
            ),
            (
                ["--post-convert", "-c"],
                {
                    "help": "Apply additional conversion to the secret after saving",
                    "choices": ["pfx-split-pem"],
                    "action": "store",
                    "dest": "convert_action",
                },
            ),
            (
                ["--post-convert-pfx-pwd", "-p"],
                {
                    "help": "PFX password to use in 'pfx-split-pem' conversion \
                        (if not set, assumes no password is required)",
                    "action": "store",
                    "dest": "pfx_password",
                },
            ),
            (
                ["--post-hook", "-s"],
                {
                    "help": "Command to be run in a shell after secret saved \
                        to the file. Executed after all additional conversions \
                        an only if the file with secret has been created or updated.",
                    "action": "store",
                    "dest": "post_hook",
                },
            ),
            (
                ["--vault", "-kv"],
                {
                    "help": "Azure Key Vault name to fetch the secret from \
                        (could be repetated)",
                    "action": "append",
                    "metavar": "NAME",
                    "dest": "vault_list",
                },
            ),
        ],
    )
    def save(self) -> None:
        """Fetch secret from first available Azure Key Vault.

        Expects CLI positional argument to contain the name of the secret
        to be searched.

        By default, iterates through all available Key Vaults until first
        match is found. Alternatively, the list could be scoped to specific
        Key Vaults with the CLI option ``--vault NAME`` mentioned multiple times.

        """
        secret_name: str = self.app.pargs.secret_name

        file_path_secret: Path = Path(self.app.pargs.file_path_secret)

        file_path_secret_tmp: Path = file_path_secret.with_suffix(".tmp")

        file_secret_updated: bool = False

        base64_decode: bool = self.app.pargs.b64decode

        convert_action: str = self.app.pargs.convert_action

        pfx_password: str = self.app.pargs.pfx_password

        post_hook: str = self.app.pargs.post_hook

        secret: Optional[KeyVaultSecret] = None

        secret_output: bytes = ""

        # get list of applicable key vaults
        vault_list: List[str] = self._get_vaults("vault_list")

        if len(vault_list) > 0:
            self.app.log.info(
                "Fetching secret '{}' from '{}'".format(
                    secret_name, ", ".join(vault_list)
                )
            )
            for vault in vault_list:
                secret = self._get_secret(vault, secret_name)

                if secret:
                    break

            if secret:
                if base64_decode:
                    self.app.log.info("Base64-decoding secret '{}'".format(secret_name))

                    try:
                        secret_output = standard_b64decode(secret.value)

                    except BinAsciiError as e:
                        self.app.log.error("Base64 decoding error: {}".format(str(e)))

                        secret_output = secret.value.encode()

                else:
                    secret_output = secret.value.encode()

                self.app.log.info(
                    "Saving secret '{}' to temporary file '{}'".format(
                        secret_name, file_path_secret_tmp
                    )
                )
                with open(file_path_secret_tmp, "wb") as f:
                    f.write(secret_output)

                file_path_secret_tmp.chmod(0o600)

                if not file_path_secret.exists():
                    self.app.log.info(
                        "Target file '{}' does not exist, renaming '{}' as target".format(  # noqa: E501
                            file_path_secret, file_path_secret_tmp
                        )
                    )
                    file_path_secret_tmp.rename(file_path_secret)

                    file_secret_updated = True

                else:
                    self.app.log.info(
                        "Target file '{}' exists, checking against '{}'".format(
                            file_path_secret, file_path_secret_tmp
                        )
                    )

                    hash_tmp = sha256()
                    with open(file_path_secret_tmp, "rb") as f:
                        hash_tmp.update(f.read())
                    self.app.log.info(
                        "Temporary file '{}' digest: '{}:{}'".format(
                            file_path_secret_tmp, hash_tmp.name, hash_tmp.hexdigest()
                        )
                    )

                    hash_target = sha256()
                    with open(file_path_secret, "rb") as f:
                        hash_target.update(f.read())
                    self.app.log.info(
                        "Target file '{}' digest: '{}:{}'".format(
                            file_path_secret, hash_target.name, hash_target.hexdigest()
                        )
                    )

                    if hash_target.digest() == hash_tmp.digest():
                        self.app.log.info(
                            "Target and temporary files are identical, stop processing"
                        )
                        self.app.log.info(
                            "Removing temporary file '{}'".format(file_path_secret_tmp)
                        )

                        file_path_secret_tmp.unlink()

                        file_secret_updated = False

                    else:
                        self.app.log.info(
                            "Target and temporary files are different, continue processing"  # noqa: E501
                        )
                        self.app.log.info(
                            "Renaming temporary file '{}' as target file '{}'".format(
                                file_path_secret_tmp, file_path_secret
                            )
                        )
                        file_path_secret_tmp.rename(file_path_secret)

                        file_secret_updated = True

                if file_secret_updated:
                    if convert_action == "pfx-split-pem":
                        private_key: RSAPrivateKey
                        certificate: Certificate
                        additional_certificates: List[Certificate]

                        file_path_key_pem: Path = file_path_secret.with_name(
                            "{}_key".format(file_path_secret.stem)
                        ).with_suffix(".pem")

                        file_path_cert_pem: Path = file_path_secret.with_name(
                            "{}_cert".format(file_path_secret.stem)
                        ).with_suffix(".pem")

                        self.app.log.info(
                            "Applying '{}' conversion to secret '{}'".format(
                                convert_action, secret_name
                            )
                        )
                        try:
                            (
                                private_key,
                                certificate,
                                additional_certificates,
                            ) = pkcs12.load_key_and_certificates(
                                secret_output, pfx_password, default_backend()
                            )

                        except ValueError as e:
                            self.app.log.error("ValueError: {}".format(str(e)))

                        else:
                            self.app.log.info(
                                "Saving private key from '{}' as PEM to '{}'".format(
                                    secret_name, file_path_key_pem
                                )
                            )
                            private_key_pem = private_key.private_bytes(
                                encoding=serialization.Encoding.PEM,
                                format=serialization.PrivateFormat.PKCS8,
                                encryption_algorithm=serialization.NoEncryption(),
                            )
                            with open(file_path_key_pem, "wb") as f:
                                f.write(private_key_pem)

                            file_path_key_pem.chmod(0o600)

                            self.app.log.info(
                                "Saving certificate from '{}' as PEM to '{}'".format(
                                    secret_name, file_path_cert_pem
                                )
                            )
                            certificate_pem = certificate.public_bytes(
                                encoding=serialization.Encoding.PEM
                            )
                            with open(file_path_cert_pem, "wb") as f:
                                f.write(certificate_pem)

                                for intermediate_cert in additional_certificates:
                                    intermediate_cert_pem = intermediate_cert.public_bytes(  # noqa: E501
                                        encoding=serialization.Encoding.PEM
                                    )

                                    f.write(intermediate_cert_pem)

                            file_path_cert_pem.chmod(0o600)

                    if post_hook:
                        self.app.log.info(
                            "Executing post-hook shell command '{}'".format(post_hook)
                        )
                        stdout, stderr, exitcode = shell.cmd(post_hook)

                        if exitcode == 0:
                            self.app.log.info(
                                "Post-hook shell command executed successfully"
                            )

                        else:
                            self.app.log.error(
                                "Post-hook shell command exited with code '{}'".format(
                                    exitcode
                                )
                            )
                            self.app.log.error(
                                "Post-hook shell command error message '{}'".format(
                                    stderr.decode().rstrip()
                                )
                            )

                        self.app.log.info(
                            "Post-hook shell command output '{}'".format(
                                stdout.decode().rstrip()
                            )
                        )

    @ex(
        help="search secret in all available Azure Key Vaults",
        arguments=[
            (
                ["--name", "-n"],
                {
                    "help": "name of the secret",
                    "action": "store",
                    "metavar": "SECRET_NAME",
                    "required": True,
                    "dest": "secret_name",
                },
            ),
            (
                ["--vault", "-kv"],
                {
                    "help": "Azure Key Vault name to fetch the secret from \
                        (could be repetated)",
                    "action": "append",
                    "metavar": "NAME",
                    "dest": "vault_list",
                },
            ),
        ],
    )
    def search(self) -> None:
        """Search secret in all Azure Key Vaults.

        Expects CLI positional argument to contain the name of the secret
        to be searched.

        By default, iterates through all available Key Vaults. Alternatively,
        the list could be scoped to specific Key Vaults with the CLI option
        ``--vault NAME`` mentioned multiple times.

        """
        # get secret's name from CLI params
        secret_name: str = self.app.pargs.secret_name

        # get list of applicable key vaults
        vault_list: List[str] = self._get_vaults("vault_list")

        if len(vault_list) > 0:
            self.app.log.info(
                "Searching secret '{}' in '{}'".format(
                    secret_name, ", ".join(vault_list)
                )
            )

            output_data: Dict[str, List[KeyVaultSecret]] = {"secrets": []}

            for vault in vault_list:
                secret = self._get_secret(vault, secret_name)

                if secret is not None:
                    output_data["secrets"].append(
                        {
                            "vault_name": vault,
                            "name": secret.properties.name,
                            "created_on": secret.properties.created_on.strftime(
                                "%Y-%m-%dT%H:%M:%SZ%z"
                            )
                            if secret.properties.created_on
                            else "Undefined",
                            "expires_on": secret.properties.expires_on.strftime(
                                "%Y-%m-%dT%H:%M:%SZ%z"
                            )
                            if secret.properties.expires_on
                            else "Undefined",
                            "version": secret.properties.version,
                        }
                    )

            self.app.render(output_data, "secrets_search.j2")

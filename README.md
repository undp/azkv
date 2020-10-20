# AzKV

[![Python 3.6+](https://img.shields.io/badge/Python-3.6+-blue.svg)][PythonRef] [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)][BlackRef] [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)][MITRef]

[PythonRef]: https://docs.python.org/3.6/
[BlackRef]: https://github.com/ambv/black
[MITRef]: https://opensource.org/licenses/MIT

`AzKV` is a CLI client for the Azure Key Vault data plane with support for redundant vaults. It addresses the high reliability scenarios where it is expected that if a Key Vault is not available due to the Azure region-wide failure, the same data could be retrieved from a redundant Key Vault deployed in another unaffected region.

There is a [native Azure VM extension][AzExtKeyVaultRef] for Linux and Windows that could fetch the certificate and the corresponding secret key. It also performs a periodic check to see if the certificate has been changed and needs to be updated.

[AzExtKeyVaultRef]: https://azure.microsoft.com/en-us/updates/azure-key-vault-virtual-machine-extension-now-generally-available/

While this native extension can monitor a list of certificates, they all are fetched individually. So, if the certificate or the Key Vault are not available, there is no retry against a different vault. There is no straightforward hooking functionality to run a shell command if data is updated on the local file system. This extension also has limited support for different Linux distributions and does not support `RHEL` or `CentOS`.

At this point `AzKV` addresses these limitations of the native Azure VM extension. It allows to fetch PKCS12-formatted blobs form Azure Key Vault, BASE64-decode the data, extract certificate and private key from the PKCS12 package and save/update data on the file system in the PEM format, if retrieved content is different from what has been already saved. It also delivers a post-update hook functionality that allows to execute shell commands upon successful update. This post-update hook could be used to restart a service consuming the certificate/key when content is updated.

While geared primarily towards fetching certificates from Key Vaults, current version of the tool could be also used to fetch secrets like passwords and incorporate them in your server or app configuration.

## Getting Started

### Installing

`AzKV` is distributed through the [Python Package Index][PyPIRef] as [azkv][PyPIProjRef]. Run the following command to:

[PyPIRef]: https://pypi.org
[PyPIProjRef]:https://pypi.org/project/azkv/

* install a specific version

    ```sh
    pip install "azkv==0.1"
    ```

* install the latest version

    ```sh
    pip install "azkv"
    ```

* upgrade to the latest version

    ```sh
    pip install --upgrade "azkv"
    ```

* install optional DEV dependencies like `pytest` framework and plugins necessary for performance and functional testing

    ```sh
    pip install "azkv[test]"
    ```

### Configuring

`AzKV` looks for the `YAML` configuration file in the following locations:

* `/etc/azkv/azkv.yaml`
* `~/.config/azkv/azkv.yaml`
* `~/.azkv/config/azkv.yaml`
* `~/.azkv.yaml`

Here is the [example configuration file][AzKVConfigRef]:

[AzKVConfigRef]: config/etc/azkv_example.yaml

```yaml
### AzKV Configuration Settings
---
azkv:
  # Toggle application level debug (does not toggle Cement framework debugging)
  # debug: false

  # Common credentials to be used for all vaults, unless some specific vaults
  # have `credentials` property defined that overrides the common one.
  credentials:
    # Type of Azure credentials to use for Key Vault access.
    # Possible values are:
    # * `EnvironmentVariables` -  uses `EnvironmentCredential` to pickup service principal or user
    #            credentials from environment variables.
    #
    # * `SystemManagedIdentity` - uses `ManagedIdentityCredential` class configured for system-assigned
    #            managed identity.
    #
    # * `UserManagedIdentity` - uses `ManagedIdentityCredential` class configured for user-assigned
    #            managed identity. Requires `client_id` or will be reduced to `SystemManagedIdentity`
    type: EnvironmentVariables
    # ClientID for the user-assigned managed identity; option required only for `type: UserManagedIdentity`
    # client_id: 2343556b-7153-470a-908a-b3837db7ec88

  # List of Azure Key Vaults to be referenced in AzKV operations
  keyvaults:
    # Short name for a Key Vault (used in logs and CLI options)
    foo-prod-eastus:
      # URL for the Azure Key Vault API endpoint
      url: "https://foo-prod-eastus.vault.azure.net/"
      # Credentials specific to this Key Vault. Supersedes common credentials above.
      credentials:
        type: UserManagedIdentity
        client_id: 2343556b-7153-470a-908a-b3837db7ec88
    foo-prod-uksouth:
      url: "https://foo-prod-uksouth.vault.azure.net/"
      credentials:
        type: SystemManagedIdentity
    foo-prod-ukwest:
      url: "https://foo-prod-ukwest.vault.azure.net/"

# Logging configuration
log.colorlog:
  # Whether or not to colorize the log file.
  # colorize_file_log: false

  # Whether or not to colorize the console log.
  # colorize_console_log: true

  # Where the log file lives (no log file by default)
  # file: null

  # The level for which to log.  One of: info, warning, error, fatal, debug
  # level: INFO

  # Whether or not to log to console
  # to_console: true

  # Whether or not to rotate the log file when it reaches `max_bytes`
  # rotate: false

  # Max size in bytes that a log file can grow until it is rotated.
  # max_bytes: 512000

  # The maximun number of log files to maintain when rotating
  # max_files: 4
```

## Usage



## Requirements

* Python >= 3.6

## Built using

* [Cement Framework][CementRef] - CLI application framework

[CementRef]: https://builtoncement.com/

## Versioning

We use [Semantic Versioning Specification][SemVer] as a version numbering convention.

[SemVer]: http://semver.org/

## Release History

For the available versions, see the [tags on this repository][RepoTags]. Specific changes for each version are documented in [CHANGELOG.md][ChangelogRef].

Also, conventions for `git commit` messages are documented in [CONTRIBUTING.md][ContribRef].

[RepoTags]: https://github.com/undp/azkv/tags
[ChangelogRef]: CHANGELOG.md
[ContribRef]: CONTRIBUTING.md

## Authors

* **Oleksiy Kuzmenko** - [OK-UNDP@GitHub][OK-UNDP@GitHub] - *Initial design and implementation*

[OK-UNDP@GitHub]: https://github.com/OK-UNDP

## Acknowledgments

* Hat tip to all individuals shaping design of this project by sharing their knowledge in articles, blogs and forums.

## License

Unless otherwise stated, all authors (see commit logs) release their work under the [MIT License][MITRef]. See [LICENSE.md][LicenseRef] for details.

[LicenseRef]: LICENSE.md

## Contributing

There are plenty of ways you could contribute to this project. Feel free to:

* submit bug reports and feature requests
* outline, fix and expand documentation
* peer-review bug reports and pull requests
* implement new features or fix bugs

See [CONTRIBUTING.md][ContribRef] for details on code formatting, linting and testing frameworks used by this project.

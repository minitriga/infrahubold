# `infrahubctl check`

Execute user-defined checks.

**Usage**:

```console
$ infrahubctl check [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `run`: Locate and execute all checks under the...

## `infrahubctl check run`

Locate and execute all checks under the defined path.

**Usage**:

```console
$ infrahubctl check run [OPTIONS] [PATH]
```

**Arguments**:

* `[PATH]`: [default: .]

**Options**:

* `--branch TEXT`
* `--rebase / --no-rebase`: [default: rebase]
* `--debug / --no-debug`: [default: no-debug]
* `--format-json / --no-format-json`: [default: no-format-json]
* `--help`: Show this message and exit.
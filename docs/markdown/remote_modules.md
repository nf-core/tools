---
title: Modules
subtitle: Remote modules
---

With the advent of [Nextflow DSL2](https://www.nextflow.io/docs/latest/dsl2.html), we are creating a centralised repository of modules.
These are software tool process definitions that can be imported into any pipeline.
This allows multiple pipelines to use the same code for share tools and gives a greater degree of granulairy and unit testing.

The nf-core DSL2 modules repository is at <https://github.com/nf-core/modules>

# Custom remote modules

The modules supercommand comes with two flags for specifying a custom remote:

- `--github-repository <github repo>`: Specify the repository from which the modules should be fetched. Defaults to `nf-core/modules`.
- `--branch <branch name>`: Specify the branch from which the modules shoudl be fetched. Defaults to `master`.

Note that a custom remote must follow a similar directory structure to that of `nf-core/moduleś` for the `nf-core modules` commands to work properly.

# Private remote modules

In order to get access to your private modules repo, you need to create
the `~/.config/gh/hosts.yml` file, which is the same file required by
[GitHub CLI](https://cli.github.com/) to deal with private repositories.
Such file is structured as follow:

```conf
github.com:
    oauth_token: <your github access token>
    user: <your github user>
    git_protocol: <ssh or https are valid choices>
```

The easiest way to create this configuration file is through _GitHub CLI_: follow
its [installation instructions](https://cli.github.com/manual/installation)
and then call:

```bash
gh auth login
```

After that, you will be able to list and install your private modules without
providing your github credentials through command line, by using `--github-repository`
and `--branch` options properly.
See the documentation on [gh auth login](https://cli.github.com/manual/gh_auth_login>)
to get more information.

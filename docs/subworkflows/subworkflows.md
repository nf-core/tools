---
title: nf-core subworkflows
description: Combine multiple modules into a single subworkflow.
weight: 10
section: subworkflows
---

After the launch of nf-core modules, we can provide now also nf-core subworkflows to fully utilize the power of DSL2 modularization.
Subworkflows are chains of multiple module definitions that can be imported into any pipeline.
This allows multiple pipelines to use the same code for a the same tasks, and gives a greater degree of reusability and unit testing.

To allow us to test modules and subworkflows together we put the nf-core DSL2 subworkflows into the `subworkflows` directory of the modules repository is at <https://github.com/nf-core/modules>.

### Custom remote subworkflows

The subworkflows supercommand released in nf-core/tools version 2.7 comes with two flags for specifying a custom remote repository:

- `--git-remote <git remote url>`: Specify the repository from which the subworkflows should be fetched as a git URL. Defaults to the github repository of `nf-core/modules`.
- `--branch <branch name>`: Specify the branch from which the subworkflows should be fetched. Defaults to the default branch of your repository.

For example, if you want to install the `bam_stats_samtools` subworkflow from the repository `nf-core/modules-test` hosted at `gitlab.com` in the branch `subworkflows`, you can use the following command:

```bash
nf-core subworkflows --git-remote git@gitlab.com:nf-core/modules-test.git --branch subworkflows install bam_stats_samtools
```

Note that a custom remote must follow a similar directory structure to that of `nf-core/modules` for the `nf-core subworkflows` commands to work properly.

The directory where subworkflows are installed will be prompted or obtained from `org_path` in the `.nf-core.yml` file if available. If your subworkflows are located at `subworkflows/my-folder/SUBWORKFLOW_NAME` your `.nf-core.yml` file should have:

```yaml
org_path: my-folder
```

Please avoid installing the same tools from two different remotes, as this can lead to further errors.

The subworkflows commands will during initalisation try to pull changes from the remote repositories. If you want to disable this, for example due to performance reason or if you want to run the commands offline, you can use the flag `--no-pull`. Note however that the commands will still need to clone repositories that have previously not been used.

### Private remote repositories

You can use the subworkflows command with private remote repositories. Make sure that your local `git` is correctly configured with your private remote
and then specify the remote the same way you would do with a public remote repository.

### Custom remote subworkflows

The subworkflows supercommand released in nf-core/tools version 2.7 comes with two flags for specifying a custom remote repository:

- `--git-remote <git remote url>`: Specify the repository from which the subworkflows should be fetched as a git URL. Defaults to the github repository of `nf-core/modules`.
- `--branch <branch name>`: Specify the branch from which the subworkflows should be fetched. Defaults to the default branch of your repository.

For example, if you want to install the `bam_stats_samtools` subworkflow from the repository `nf-core/modules-test` hosted at `gitlab.com` in the branch `subworkflows`, you can use the following command:

```bash
nf-core subworkflows --git-remote git@gitlab.com:nf-core/modules-test.git --branch subworkflows install bam_stats_samtools
```

Note that a custom remote must follow a similar directory structure to that of `nf-core/modules` for the `nf-core subworkflows` commands to work properly.

The directory where subworkflows are installed will be prompted or obtained from `org_path` in the `.nf-core.yml` file if available. If your subworkflows are located at `subworkflows/my-folder/SUBWORKFLOW_NAME` your `.nf-core.yml` file should have:

```yaml
org_path: my-folder
```

Please avoid installing the same tools from two different remotes, as this can lead to further errors.

The subworkflows commands will during initalisation try to pull changes from the remote repositories. If you want to disable this, for example due to performance reason or if you want to run the commands offline, you can use the flag `--no-pull`. Note however that the commands will still need to clone repositories that have previously not been used.

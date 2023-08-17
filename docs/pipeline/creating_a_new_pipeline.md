---
title: Create a new pipeline
description: Create a pipeline from the nf-core template.
weight: 60
section: pipelines
---

The `create` subcommand makes a new pipeline using the nf-core base template.
With a given pipeline name, description and author, it makes a starter pipeline which follows nf-core best practices.

After creating the files, the command initialises the folder as a git repository and makes an initial commit.
This first "vanilla" commit which is identical to the output from the templating tool is important, as it allows us to keep your pipeline in sync with the base template in the future.
See the [nf-core syncing docs](https://nf-co.re/developers/sync) for more information.

<!-- RICH-CODEX
working_dir: tmp
-->

![` nf-core create -n nextbigthing -d "This pipeline analyses data from the next big omics technique" -a "Big Steve" --plain`](../images/nf-core-create.svg)

Once you have run the command, create a new empty repository on GitHub under your username (not the `nf-core` organisation, yet) and push the commits from your computer using the example commands in the above log.
You can then continue to edit, commit and push normally as you build your pipeline.

Please see the [nf-core documentation](https://nf-co.re/developers/adding_pipelines) for a full walkthrough of how to create a new nf-core workflow.

:::tip
As the log output says, remember to come and discuss your idea for a pipeline as early as possible!
See the [documentation](https://nf-co.re/developers/adding_pipelines#join-the-community) for instructions.
:::

Note that if the required arguments for `nf-core create` are not given, it will interactively prompt for them. If you prefer, you can supply them as command line arguments. See `nf-core create --help` for more information.

### Customizing the creation of a pipeline

The `nf-core create` command comes with a number of options that allow you to customize the creation of a pipeline if you intend to not publish it as an
nf-core pipeline. This can be done in two ways: by using interactive prompts, or by supplying a `template.yml` file using the `--template-yaml <file>` option.
Both options allow you to specify a custom pipeline prefix to use instead of the common `nf-core`, as well as selecting parts of the template to be excluded during pipeline creation.
The interactive prompts will guide you through the pipeline creation process. An example of a `template.yml` file is shown below.

```yaml
name: coolpipe
description: A cool pipeline
author: me
prefix: myorg
skip:
  - github
  - ci
  - github_badges
  - igenomes
  - nf_core_configs
```

This will create a pipeline called `coolpipe` in the directory `myorg-coolpipe` (`<prefix>-<name>`) with `me` as the author. It will exclude all possible parts of the template:

- `github`: removed all files required for GitHub hosting of the pipeline. Specifically, the `.github` folder and `.gitignore` file.
- `ci`: removes the GitHub continuous integration tests from the pipeline. Specifically, the `.github/workflows/` folder.
- `github_badges`: removes GitHub badges from the `README.md` file.
- `igenomes`: removes pipeline options related to iGenomes. Including the `conf/igenomes.config` file and all references to it.
- `nf_core_configs`: excludes `nf_core/configs` repository options, which make multiple config profiles for various institutional clusters available.

To run the pipeline creation silently (i.e. without any prompts) with the nf-core template, you can use the `--plain` option.

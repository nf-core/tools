---
title: Modules
subtitle: Bump bioconda and container versions of modules
---

# Bump bioconda and container versions of modules

If you are contributing to the `nf-core/modules` repository and want to bump bioconda and container versions of certain modules, you can use the `nf-core modules bump-versions` helper tool. This will bump the bioconda version of a single or all modules to the latest version and also fetch the correct Docker and Singularity container tags.

```console
$ nf-core modules bump-versions -d modules

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2



? Bump versions for all modules or a single named module?  Named module
? Tool name: bcftools/consensus
╭───────────────────────────╮
│ [!] 1  Module updated     │
╰───────────────────────────╯
╭─────────────────────────────────────────────────────────────╮
│ Module name               │ Update message                  │
├───────────────────────────┤─────────────────────────────────┤
│ bcftools/consensus        │ Module updated:  1.11 --> 1.12  │
╰─────────────────────────────────────────────────────────────╯
```

If you don't want to update certain modules or want to update them to specific versions, you can make use of the `.nf-core.yml` configuration file. For example, you can prevent the `star/align` module from being updated by adding the following to the `.nf-core.yml` file:

```yaml
bump-versions:
  star/align: False
```

If you want this module to be updated only to a specific version (or downgraded), you could instead specifiy the version:

```yaml
bump-versions:
  star/align: "2.6.1d"
```

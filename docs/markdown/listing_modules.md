---
title: Modules
subtitle: List modules
---

# List modules

The `nf-core modules list` command provides the subcommands `remote` and `local` for listing modules installed in a remote repository and in the local pipeline respectively. Both subcommands come with the `--key <keywords>` option for filtering the modules by keywords.

## List remote modules

To list all modules available on [nf-core/modules](https://github.com/nf-core/modules), you can use
`nf-core modules list remote`, which will print all available modules to the terminal.

```console
$ nf-core modules list remote
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2


INFO     Modules available from nf-core/modules (master)

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Module Name                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ bandage/image                  │
│ bcftools/consensus             │
│ bcftools/filter                │
│ bcftools/isec                  │
│ bcftools/merge                 │
│ bcftools/mpileup               │
│ bcftools/stats                 │
│ ..truncated..                  │
└────────────────────────────────┘
```

## List installed modules

To list modules installed in a local pipeline directory you can use `nf-core modules list local`. This will list the modules install in the current working directory by default. If you want to specify another directory, use the `--dir <pipeline_dir>` flag.

```console
$ nf-core modules list local
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2


INFO     Modules installed in '.':

┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Module Name ┃ Repository      ┃ Version SHA ┃ Message                                                ┃ Date       ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ fastqc      │ nf-core/modules │ e937c79...  │ Rename software/ directory to modules/ ...truncated... │ 2021-07-07 │
│ multiqc     │ nf-core/modules │ e937c79...  │ Rename software/ directory to modules/ ...truncated... │ 2021-07-07 │
└─────────────┴─────────────────┴─────────────┴────────────────────────────────────────────────────────┴────────────┘
```

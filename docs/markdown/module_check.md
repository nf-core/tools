---
title: Modules
subtitle: Check a module against nf-core guidelines
---


# Check a module against nf-core guidelines

Run the `nf-core modules lint` command to check modules in the current working directory (pipeline or nf-core/modules clone) against nf-core guidelines.

Use the `--all` flag to run linting on all modules found. Use `--dir <pipeline_dir>` to specify another directory than the current working directory.

```console
$ nf-core modules lint
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

? Lint all modules or a single named module? Named module
? Tool name: star/align
INFO     Linting pipeline: .
INFO     Linting module: star/align
╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Module lint results                                                                                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ [!] 1 Test Warning                                                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────────────────┬────────────────────────────────────────────┬───────────────────────────────────────────────────╮
│ Module name       │ File path                                  │ Test message                                      │
├───────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ star/align        │ modules/nf-core/modules/star/align/main.nf │ Conda update: bioconda::star 2.6.1d -> 2.7.9a     │
╰───────────────────┴────────────────────────────────────────────┴───────────────────────────────────────────────────╯
╭──────────────────────╮
│ LINT RESULTS SUMMARY │
├──────────────────────┤
│ [✔]  21 Tests Passed │
│ [!]   1 Test Warning │
│ [✗]   0 Test Failed  │
╰──────────────────────╯
```

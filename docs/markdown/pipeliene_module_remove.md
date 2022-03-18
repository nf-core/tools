---
title: Modules
subtitle: Remove a module from a pipeline
---

# Remove a module from a pipeline

To delete a module from your pipeline, run `nf-core modules remove`.

```console
$ nf-core modules remove

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

? Tool name: star/align
INFO     Removing star/align
```

You can pass the module name as an optional argument to `nf-core modules remove` instead of using the cli prompt, eg: `nf-core modules remove fastqc`. To specify the pipeline directory, use `--dir <pipeline_dir>`.

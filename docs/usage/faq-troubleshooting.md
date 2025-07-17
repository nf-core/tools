# Troubleshooting and FAQs

## Why is any error or failed process from SPADES/FLYE get ignored?

If there are too few reads or the quality of the reads is low, `spades` or `flye` will fail to call any contigs or scaffold. If you want to change this behaviour, you can override the `errorStrategy` in your own Nextflow configuration file.

```nextflow
process {
    withName: SPADES {
        errorStrategy = 'retry'
    }
}
process {
    withName: FLYE {
        errorStrategy = 'retry'
    }
}
```

## Why is any error or failed process from MEDAKA get ignored?

If there are too few reads or the quality of the reads is low, `medaka` will fail to call a consensus sequence, so the output will be empty. If you want to change this behaviour, you can override the `errorStrategy` in your own Nextflow configuration file.

```nextflow
process {
    withName: MEDAKA {
        errorStrategy = 'retry'
    }
}
```

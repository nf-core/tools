---
title: Listing pipelines
description: List all nf-core pipelines and filter by keywords.
weight: 20
section: pipelines
---

The command `nf-core list` shows all available nf-core pipelines along with their latest version, when that was published and how recently the pipeline code was pulled to your local system (if at all).

An example of the output from the command is as follows:

<!-- RICH-CODEX head: 19 -->

![`nf-core list`](../images/nf-core-list.svg)

To narrow down the list, supply one or more additional keywords to filter the pipelines based on matches in titles, descriptions and topics:

![`nf-core list rna rna-seq`](../images/nf-core-list-rna.svg)

You can sort the results by latest release (`-s release`, default),
when you last pulled a local copy (`-s pulled`),
alphabetically (`-s name`),
or number of GitHub stars (`-s stars`).

<!-- RICH-CODEX head: 18 -->

![`nf-core list -s stars`](../images/nf-core-list-stars.svg)

To return results as JSON output for downstream use, use the `--json` flag.

Archived pipelines are not returned by default. To include them, use the `--show_archived` flag.

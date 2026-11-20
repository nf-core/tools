"""CodSpeed wall-time benchmarks for `nf-core pipelines` commands."""


def test_pipelines_create(benchmark_cli, tmp_path):
    """`nf-core pipelines create` with all options given, so it doesn't prompt."""
    benchmark_cli(
        "pipelines",
        "create",
        "--name",
        "benchmark",
        "--description",
        "benchmark pipeline",
        "--author",
        "nf-core",
        "--outdir",
        tmp_path / "pipeline",
        "--force",  # every round after the first writes into the same directory
        rounds=3,
    )


def test_pipelines_lint(benchmark_cli, generated_pipeline):
    """`nf-core pipelines lint` on a freshly created pipeline."""
    benchmark_cli("pipelines", "lint", "--dir", generated_pipeline, rounds=2, check=False)


def test_pipelines_schema_lint(benchmark_cli, generated_pipeline):
    """`nf-core pipelines schema lint` on a freshly created pipeline.

    Passes the schema path, as the `<pipeline schema>` default is resolved against the cwd, not `--dir`.
    """
    benchmark_cli("pipelines", "schema", "lint", generated_pipeline / "nextflow_schema.json")

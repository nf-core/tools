# .nf-core.yml configuration

The `.nf-core.yml` file at the root of any nf-core repository controls how nf-core
tools behaves for that repository. It is read by `load_tools_config()` and validated
against the `NFCoreYamlConfig` Pydantic model.

## Minimal examples

Pipeline repository:

```yaml
repository_type: pipeline
nf_core_version: "3.2.0"
```

Modules repository:

```yaml
repository_type: modules
nf_core_version: "3.2.0"
container-registry:
  - community.wave.seqera.io/library/
```

## Schema

### Top-level `.nf-core.yml` schema (`NFCoreYamlConfig`)

```{eval-rst}
.. autopydantic_model:: nf_core.utils.NFCoreYamlConfig
    :members:
    :undoc-members:
    :show-inheritance:
    :model-show-json: false
    :model-show-config-summary: false
    :model-show-validator-members: false
    :model-show-field-summary: true
    :field-show-alias: true
```

### `lint` block (`NFCoreYamlLintConfig`)

```{eval-rst}
.. autopydantic_model:: nf_core.utils.NFCoreYamlLintConfig
    :members:
    :undoc-members:
    :show-inheritance:
    :model-show-json: false
    :model-show-config-summary: false
    :model-show-validator-members: false
    :model-show-field-summary: true
    :field-show-alias: true
```

### `template` block (`NFCoreTemplateConfig`)

```{eval-rst}
.. autopydantic_model:: nf_core.utils.NFCoreTemplateConfig
    :members:
    :undoc-members:
    :show-inheritance:
    :model-show-json: false
    :model-show-config-summary: false
    :model-show-validator-members: false
    :model-show-field-summary: true
    :field-show-alias: true
```

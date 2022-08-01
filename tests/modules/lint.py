import nf_core.modules


def test_modules_lint_trimgalore(self):
    """Test linting the TrimGalore! module"""
    self.mods_install.install("trimgalore")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
    module_lint.lint(print_results=False, module="trimgalore")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_empty(self):
    """Test linting a pipeline with no modules installed"""
    self.mods_remove.remove("fastqc")
    self.mods_remove.remove("multiqc")
    self.mods_remove.remove("custom/dumpsoftwareversions")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
    module_lint.lint(print_results=False, all_modules=True)
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) == 0
    assert len(module_lint.warned) == 0


def test_modules_lint_new_modules(self):
    """lint all modules in nf-core/modules repo clone"""
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=True, all_modules=True)
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0

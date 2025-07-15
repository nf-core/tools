import os
from urllib.parse import urlparse
from reftrace import Module, ConfigFile
from reftrace.directives import Container, ContainerFormat
from reftrace.linting import LintError, LintWarning, LintResults, rule, configrule
from typing import Union, Tuple, List

# Config file rules

def directive_violating(directive):
    """Check if a directive config violates the closure rule"""
    if directive.value:
        if value_violating(directive.value):
            return LintError(
                directive.line_number,
                f"Directive {directive.name} violates closure rule")
    else:
        for option in directive.options:
            if option.name == "mode" and directive.name == "publishDir":
                # mode: of publishDir doesn't accept a closure
                continue
            if value_violating(option.value):
                return LintError(
                    option.line_number,
                    f"Directive option {option.name} of directive {directive.name} violates closure rule")
    return None

def value_violating(directive_value):
    """Check if a directive value violates the closure rule

    Directive values are the actual content of the directive config.
    For example:
    ext.args = '--num_alignments 1 -v'
    The value is '--num_alignments 1 -v'
    """
    # if a directive value does not have params, we don't need a closure
    if not directive_value.params:
        return False
    # if a directive has params, it must be nested in a closure
    return not directive_value.in_closure

@configrule
def must_use_closures(config: ConfigFile, results: LintResults):
    """All directives that use params must be nested in a closure"""
    for process_scope in config.process_scopes:
        for directive in process_scope.directives:
            error = directive_violating(directive)
            if error:
                results.errors.append(error)
        for named_scope in process_scope.named_scopes:
            for directive in named_scope.directives:
                error = directive_violating(directive)
                if error:
                    results.errors.append(error)

# Process label rules

CORRECT_PROCESS_LABELS = [
    "process_single",
    "process_low",
    "process_medium",
    "process_high",
    "process_long",
    "process_high_memory",
]

@rule
def conflicting_labels(module: Module, results: LintResults):
    for process in module.processes:
        labels = process.labels
        good_labels = [label for label in labels 
                      if label.label in CORRECT_PROCESS_LABELS]
        if len(good_labels) > 1:
            label_names = [label.label for label in good_labels]
            results.warnings.append(
                LintWarning(
                    line=process.line,
                    warning=f"process '{process.name}' has conflicting labels: {label_names}"
                )
            )

@rule
def no_standard_label(module: Module, results: LintResults):
    for process in module.processes:
        labels = process.labels
        good_labels = [label for label in labels 
                      if label.label in CORRECT_PROCESS_LABELS]
        if len(good_labels) == 0:
            results.warnings.append(
                LintWarning(
                    line=process.line,
                    warning=f"process '{process.name}' has no standard label"
                )
            )

@rule
def non_standard_label(module: Module, results: LintResults):
    for process in module.processes:
        labels = process.labels
        bad_labels = [label for label in labels 
                     if label.label not in CORRECT_PROCESS_LABELS]
        if bad_labels:
            label_names = [label.label for label in bad_labels]
            results.warnings.append(
                LintWarning(
                    line=process.line,
                    warning=f"process '{process.name}' has non-standard labels: {label_names}"
                )
            )

@rule
def duplicate_labels(module: Module, results: LintResults):
    for process in module.processes:
        labels = process.labels
        label_count = {}
        for label in labels:
            label_count[label.label] = label_count.get(label.label, 0) + 1
            
        for label_name, count in label_count.items():
            if count > 1:
                results.warnings.append(
                    LintWarning(
                        line=process.line,
                        warning=f"process '{process.name}' has duplicate label '{label_name}' ({count} times)"
                    )
                )

@rule
def no_labels(module: Module, results: LintResults):
    for process in module.processes:
        labels = process.labels
        if not labels:
            results.warnings.append(
                LintWarning(
                    line=process.line,
                    warning=f"process '{process.name}' has no labels"
                )
            )

@rule
def alphanumerics(module: Module, results: LintResults):
    
    def check_fn(label: str) -> str:
        for char in label:
            if not (char.isalnum() or char == '_'):
                return f"process label '{label}' contains non-alphanumeric characters (only letters, numbers and underscores recommended)"
        return ""
    
    for process in module.processes:
        labels = process.labels
        for label in labels:
            if msg := check_fn(label.label):
                results.warnings.append(
                    LintWarning(
                        line=label.line,
                        warning=msg
                    )
                )

# Container rules

def container_names(container: Container) -> List[str]:
    """Get all container names based on the format.
    
    Args:
        container: The container directive to get names from
        
    Returns:
        List[str]: A list of names associated with this container. For simple containers,
                  returns a single-item list. For ternary containers, returns both true
                  and false branch names if they exist.
    """
    if container.format == ContainerFormat.SIMPLE:
        return [container.simple_name] if container.simple_name else []
    elif container.format == ContainerFormat.TERNARY:
        names = []
        if container.true_name:
            names.append(container.true_name)
        if container.false_name:
            names.append(container.false_name)
        return names
    raise ValueError(f"invalid container format: {container.format}")

@rule
def container_with_space(module: Module, results: LintResults):
    for process in module.processes:
        containers = process.containers
        for container in containers:
            for name in container_names(container):
                if " " in name:
                    results.errors.append(
                        LintError(
                            line=container.line,
                            error=f"container name '{name}' contains spaces, which is not allowed"
                        )
                    )

@rule
def multiple_containers(module: Module, results: LintResults):
    for process in module.processes:
        containers = process.containers
        for container in containers:
            for name in container_names(container):
                if "biocontainers/" in name and ("https://containers" in name or "https://depot" in name):
                    results.warnings.append(
                        LintWarning(
                            line=container.line,
                            warning="Docker and Singularity containers specified on the same line"
                        )
                    )

def is_valid_tag(tag: str) -> bool:
    if not tag:
        return False
    return all(c.isalnum() or c in '-_.' for c in tag)

def get_singularity_tag(container_name: str) -> Tuple[str, Union[str, None]]:
    try:
        parsed_url = urlparse(container_name)
        last_segment = os.path.basename(parsed_url.path)
        
        if last_segment in (".", "/"):
            return "", "invalid container URL: no path segments"
            
        last_segment = last_segment.removesuffix(".img").removesuffix(".sif")
        
        # Check for colon-separated tag
        if ":" in last_segment:
            tag = last_segment.split(":")[-1]
            if is_valid_tag(tag):
                return tag, None
                
        # Check for _v<digit> pattern
        if "_v" in last_segment:
            idx = last_segment.rindex("_v")
            if len(last_segment) > idx + 2 and last_segment[idx + 2].isdigit():
                tag = last_segment[idx + 1:]
                if is_valid_tag(tag):
                    return tag, None
                    
        return "", f"singularity container '{container_name}' must specify a tag"
    except Exception as e:
        return "", f"invalid container URL '{container_name}': {str(e)}"

def get_docker_tag(container_name: str) -> Tuple[str, Union[str, None]]:
    if ":" in container_name:
        tag = container_name.split(":")[-1]
        if not is_valid_tag(tag):
            return "", f"invalid docker tag format for container '{container_name}'"
        return tag, None
    return "", f"docker container '{container_name}' must specify a tag"

def docker_or_singularity(container_name: str) -> Tuple[str, Union[str, None]]:
    if container_name.startswith(("https://", "https://depot")):
        try:
            urlparse(container_name)
            return "singularity", None
        except Exception:
            return "", f"invalid singularity container URL '{container_name}'"
            
    if "/" in container_name or ":" in container_name:
        return "docker", None
        
    return "", f"unknown container type '{container_name}'"

@rule
def must_be_tagged(module: Module, results: LintResults):
    for process in module.processes:
        containers = process.containers
        for container in containers:
            for name in container_names(container):
                container_type, error = docker_or_singularity(name)
                if error:
                    results.errors.append(
                        LintError(
                            line=container.line,
                            error=error
                        )
                    )
                    continue
                    
                if container_type == "singularity":
                    _, error = get_singularity_tag(name)
                    if error:
                        results.errors.append(
                            LintError(
                                line=container.line,
                                error=error
                            )
                        )
                        
                elif container_type == "docker":
                    _, error = get_docker_tag(name)
                    if error:
                        results.errors.append(
                            LintError(
                                line=container.line,
                                error=error
                            )
                        )
                    
                    if name.startswith("quay.io"):
                        results.errors.append(
                            LintError(
                                line=container.line,
                                error=f"container '{name}': please use 'organization/container:tag' format instead of full registry URL"
                            )
                        )

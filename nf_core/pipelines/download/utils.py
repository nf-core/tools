import contextlib
import logging
import re
import tempfile
import textwrap
from collections.abc import Generator
from pathlib import Path

from nf_core.utils import run_cmd

log = logging.getLogger(__name__)

# This is the minimal version of Nextflow required to fetch containers with `nextflow inspect`
NF_INSPECT_MIN_NF_VERSION = (25, 4, 4)


# Pretty print a Nextflow version tuple
def pretty_nf_version(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]:02}.{version[2]}"


# Check that the Nextflow version >= the minimal version required
# This is used to ensure that we can run `nextflow inspect`
def check_nextflow_version(minimal_nxf_version: tuple[int, int, int], silent=False) -> bool:
    """Check the version of Nextflow installed on the system.

    Args:
        tuple[int, int, int]: The version of Nextflow as a tuple of integers.
    Returns:
        bool: True if the installed version is greater than or equal to `minimal_nxf_version`
    """
    try:
        cmd_out = run_cmd("nextflow", "-v")
        if cmd_out is None:
            raise RuntimeError("Failed to run Nextflow version check.")
        out, _ = cmd_out
        out_str = str(out, encoding="utf-8")  # Ensure we have a string
        version_str = out_str.strip().split()[2]
        if silent:
            log.debug(f"Detected Nextflow version {'.'.join(version_str.split('.')[:3])}")
        else:
            log.info(f"Detected Nextflow version {'.'.join(version_str.split('.')[:3])}")
        return tuple(map(int, version_str.split("."))) >= minimal_nxf_version
    except Exception as e:
        log.warning(f"Error checking Nextflow version: {e}")
        return False


class DownloadError(RuntimeError):
    """A custom exception that is raised when nf-core pipelines download encounters a problem that we already took into consideration.
    In this case, we do not want to print the traceback, but give the user some concise, helpful feedback instead.
    """


@contextlib.contextmanager
def intermediate_file(output_path: Path) -> Generator[tempfile._TemporaryFileWrapper, None, None]:
    """Context manager to help ensure the output file is either complete or non-existent.
    It does that by creating a temporary file in the same directory as the output file,
    letting the caller write to it, and then moving it to the final location.
    If an exception is raised, the temporary file is deleted and the output file is not touched.
    """
    if output_path.is_dir():
        raise DownloadError(f"Output path '{output_path}' is a directory")
    if output_path.is_symlink():
        raise DownloadError(f"Output path '{output_path}' is a symbolic link")

    tmp = tempfile.NamedTemporaryFile(dir=output_path.parent, delete=False)
    try:
        yield tmp
        tmp.close()
        Path(tmp.name).rename(output_path)
    except:
        tmp_path = Path(tmp.name)
        if tmp_path.exists():
            tmp_path.unlink()
        raise


@contextlib.contextmanager
def intermediate_file_no_creation(output_path: Path) -> Generator[Path, None, None]:
    """
    Context manager to help ensure the output file is either complete or non-existent.

    'singularity/apptainer pull' requires that the output file does not exist before it is run.
    For pulling container we therefore create a temporary directory with and write to a file named
    'tempfile' in it. If the pull command is successful, we rename the temporary file to the output path.
    """
    if output_path.is_dir():
        raise DownloadError(f"Output path '{output_path}' is a directory")
    if output_path.is_symlink():
        raise DownloadError(f"Output path '{output_path}' is a symbolic link")

    tmp = tempfile.NamedTemporaryFile(dir=output_path.parent, delete=False)
    tmp_fn = Path(tmp.name) / "tempfile"
    try:
        yield tmp_fn
        Path(tmp.name).rename(output_path)
        tmp.cleanup()
    except:
        tmp.cleanup()
        raise


##################################################################################################
#                                                                                                #
#   Below are helper functions used by the legacy method for extracting pipeline containers      #
#                                                                                                #
##################################################################################################
def rectify_raw_container_matches(raw_findings):
    """Helper function to rectify the raw extracted container matches into fully qualified container names.
    If multiple containers are found, any prefixed with http for direct download is prioritized

    Example syntax:

    Early DSL2:

    .. code-block:: groovy

        if (workflow.containerEngine == 'singularity' && !params.singularity_pull_docker_container) {
            container "https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0"
        } else {
            container "quay.io/biocontainers/fastqc:0.11.9--0"
        }

    Later DSL2:

    .. code-block:: groovy

        container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
            'https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0' :
            'biocontainers/fastqc:0.11.9--0' }"

    Later DSL2, variable is being used:

    .. code-block:: groovy

        container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
            "https://depot.galaxyproject.org/singularity/${container_id}" :
            "quay.io/biocontainers/${container_id}" }"

        container_id = 'mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:afaaa4c6f5b308b4b6aa2dd8e99e1466b2a6b0cd-0'

    DSL1 / Special case DSL2:

    .. code-block:: groovy

        container "nfcore/cellranger:6.0.2"

    """
    cleaned_matches = []

    # Thanks Stack Overflow for the regex: https://stackoverflow.com/a/3809435/713980
    url_regex = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    oras_regex = r"oras:\/\/[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    # Thanks Stack Overflow for the regex: https://stackoverflow.com/a/39672069/713980
    docker_regex = r"^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$"

    # at this point, we don't have to distinguish anymore, because we will later prioritize direct downloads over Docker URIs.
    either_url_or_docker = re.compile(f"{url_regex}|{oras_regex}|{docker_regex}", re.S)

    for _, container_value, search_space, file_path in raw_findings:
        """
        Now we need to isolate all container paths (typically quoted strings) from the raw container_value

        For example from:

        "${ workflow.containerEngine == \'singularity\' && !task.ext.singularity_pull_docker_container ?
        \'https://depot.galaxyproject.org/singularity/ubuntu:20.04\' :
        \'nf-core/ubuntu:20.04\' }"

        we want to extract

        'singularity'
        'https://depot.galaxyproject.org/singularity/ubuntu:20.04'
        'nf-core/ubuntu:20.04'

        The problem is, that we find almost arbitrary notations in container_value,
        such as single quotes, double quotes and escaped single quotes

        Sometimes target strings are wrapped into a variable to be evaluated by Nextflow,
        like in the example above.
        Sometimes the whole string is a variable "${container_name}", that is
        denoted elsewhere.

        Sometimes the string contains variables which may be defined elsewhere or
        not even known when downloading, like ${params.genome}.

        "https://depot.galaxyproject.org/singularity/ubuntu:${version}" or
        "nfcore/sarekvep:dev.${params.genome}"

        Mostly, it is a nested DSL2 string, but it may also just be a plain string.


        First, check if container_value is a plain container URI like in DSL1 pipelines
        or a plain URL like in the old DSL2 convention

        """
        direct_match = re.match(either_url_or_docker, container_value.strip())
        if direct_match:
            # eliminate known false positives also from direct matches
            if direct_match.group(0) not in ["singularity", "apptainer"]:
                cleaned_matches.append(direct_match.group(0))
            continue  # oh yes, that was plain sailing

        """
        no plain string, we likely need to break it up further

        [^\"\'] makes sure that the outermost quote character is not matched.
        (?P<quote>(?<![\\])[\'\"]) again captures the quote character, but not if it is preceded by an escape sequence (?<![\\])
        (?P<param>(?:.(?!(?<![\\])\1))*.?)\1 is basically what I used above, but again has the (?<![\\]) inserted before \1 to account for escapes.
        """

        container_value_defs = re.findall(
            r"[^\"\'](?P<quote>(?<![\\])[\'\"])(?P<param>(?:.(?!(?<![\\])\1))*.?)\1",
            container_value,
        )

        """
        eliminate known false positives and create plain list out of the tuples returned by the regex above
        example result:
        ['https://depot.galaxyproject.org/singularity/scanpy:1.7.2--pyhdfd78af_0', 'biocontainers/scanpy:1.7.2--pyhdfd78af_0']
        """
        container_value_defs = [
            capture for _, capture in container_value_defs[:] if capture not in ["singularity", "apptainer"]
        ]

        """
        For later DSL2 syntax, container_value_defs should contain both, the download URL and the Docker URI.
        For earlier DSL2, both end up in different raw_findings, so a subsequent deduplication is necessary anyway
        to not pull a container that is already downloaded directly.

        At this point, we just add everything that is either a URL or a Docker URI to cleaned matches.
        """

        valid_containers = list(filter(either_url_or_docker.match, container_value_defs))

        if valid_containers:
            cleaned_matches = cleaned_matches + valid_containers
            # Yeah, we have successfully extracted something from this raw_finding, so move on.
            continue

        """
        Neither a plain Docker URI nor a DSL2-like definition was found. This is a tricky case, then.

        Some modules declare the container as separate variable. This entails that " instead of ' is used,
        so container_value will not contain it.

        Therefore, we need to repeat the search over the raw contents, extract the variable name, and use it inside a new regex.
        This is why the raw search_space is still needed at this level.

        To get the variable name ( ${container_id} in above example ), we match the literal word "container" and use lookbehind (reset the match).
        Then we skip [^${}]+ everything that is not $ or curly braces. The next capture group is
        ${ followed by any characters that are not curly braces [^{}]+ and ended by a closing curly brace (}),
        but only if it's not followed by any other curly braces (?![^{]*}). The latter ensures we capture the innermost
        variable name.
        """

        container_definition = re.search(r"(?<=container)[^\${}]+\${([^{}]+)}(?![^{]*})", str(search_space))

        if bool(container_definition) and bool(container_definition.group(1)):
            pattern = re.escape(container_definition.group(1))
            # extract the quoted string(s) following the variable assignment
            container_names = re.findall(rf"{pattern}\s*=\s*[\"\']([^\"\']+)[\"\']", search_space)

            if bool(container_names):
                if isinstance(container_names, str):
                    cleaned_matches.append(f"https://depot.galaxyproject.org/singularity/{container_names}")

                elif isinstance(container_names, list):
                    # this deliberately appends container_names[-1] twice to cleaned_matches
                    # but deduplication is performed anyway and just setting this_container
                    # here as well allows for an easy check to see if parsing succeeded.
                    for container_name in container_names:
                        cleaned_matches.append(f"https://depot.galaxyproject.org/singularity/{container_name}")

                continue

        # all implemented options exhausted. Nothing left to be done:
        log.error(
            f"[red]Cannot parse container string in '{file_path}':\n\n{textwrap.indent(container_value, '    ')}\n\n:warning: Skipping this singularity image."
        )

    """
    Loop has finished, now we need to remove duplicates and prioritize direct downloads over containers pulled from the registries
    """
    return prioritize_direct_download(cleaned_matches)


def prioritize_direct_download(container_list: list[str]) -> list[str]:
    """
    Helper function that takes a list of container images (URLs and Docker URIs),
    eliminates all Docker URIs for which also a URL is contained and returns the
    cleaned and also deduplicated list.

    Conceptually, this works like so:

    Everything after the last Slash should be identical, e.g. "scanpy:1.7.2--pyhdfd78af_0" in
    ['https://depot.galaxyproject.org/singularity/scanpy:1.7.2--pyhdfd78af_0', 'biocontainers/scanpy:1.7.2--pyhdfd78af_0']


    re.sub('.*/(.*)','\\1',c) will drop everything up to the last slash from c (container_id)

    d.get(k:=re.sub('.*/(.*)','\\1',c),'') assigns the truncated string to k (key) and gets the
    corresponding value from the dict if present or else defaults to "".

    If the regex pattern matches, the original container_id will be assigned to the dict with the k key.
    r"^$|(?!^http)" matches an empty string (we didn't have it in the dict yet and want to keep it in either case) or
    any string that does not start with http. Because if our current dict value already starts with http,
    we want to keep it and not replace with with whatever we have now (which might be the Docker URI).

    A regex that matches http, r"^$|^http" could thus be used to prioritize the Docker URIs over http Downloads

    We also need to handle a special case: The https:// Singularity downloads from Seqera Containers all end in 'data', although
    they are not equivalent, e.g.:

    'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/63/6397750e9730a3fbcc5b4c43f14bd141c64c723fd7dad80e47921a68a7c3cd21/data'
    'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data'

    Lastly, we want to remove at least a few Docker URIs for those modules, that have an oras:// download link.
    """
    d: dict[str, str] = {}
    seqera_containers_http: list[str] = []
    seqera_containers_oras: list[str] = []
    all_others: list[str] = []

    for c in container_list:
        if bool(re.search(r"/data$", c)):
            seqera_containers_http.append(c)
        elif bool(re.search(r"^oras://", c)):
            seqera_containers_oras.append(c)
        else:
            all_others.append(c)

    for c in all_others:
        if re.match(r"^$|(?!^http)", d.get(k := re.sub(".*/(.*)", "\\1", c), "")):
            log.debug(f"{c} matches and will be saved as {k}")
            d[k] = c

    combined_with_oras = reconcile_seqera_container_uris(seqera_containers_oras, list(d.values()))

    # combine deduplicated others (Seqera containers oras, http others and Docker URI others) and Seqera containers http
    return sorted(list(set(combined_with_oras + seqera_containers_http)))


def reconcile_seqera_container_uris(prioritized_container_list: list[str], other_list: list[str]) -> list[str]:
    """
    Helper function that takes a list of Seqera container URIs,
    extracts the software string and builds a regex from them to filter out
    similar containers from the second container list.

    prioritzed_container_list = [
    ...     "oras://community.wave.seqera.io/library/multiqc:1.25.1--f0e743d16869c0bf",
    ...     "oras://community.wave.seqera.io/library/multiqc_pip_multiqc-plugins:e1f4877f1515d03c"
    ... ]

    will be cleaned to

    ['library/multiqc:1.25.1', 'library/multiqc_pip_multiqc-plugins']

    Subsequently, build a regex from those and filter out matching duplicates in other_list:
    """
    if not prioritized_container_list:
        return other_list
    else:
        # trim the URIs to the stem that contains the tool string, assign with Walrus operator to account for non-matching patterns
        trimmed_priority_list = [
            match.group()
            for c in set(prioritized_container_list)
            if (match := (re.search(r"library/.*?:[\d.]+", c) if "--" in c else re.search(r"library/[^\s:]+", c)))
        ]

        # build regex
        prioritized_containers = re.compile("|".join(f"{re.escape(c)}" for c in trimmed_priority_list))

        # filter out matches in other list
        filtered_containers = [c for c in other_list if not re.search(prioritized_containers, c)]

        # combine prioritized and regular container lists
        return sorted(list(set(prioritized_container_list + filtered_containers)))

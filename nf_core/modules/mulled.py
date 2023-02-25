"""Generate the name of a BioContainers mulled image version 2."""


from __future__ import annotations

import hashlib
import logging
import re
from typing import Iterable, List, NamedTuple, Optional, Tuple

import requests
from packaging.version import InvalidVersion, Version

log = logging.getLogger(__name__)


# Copied from galaxy.tool_util.deps.mulled.util
class Target(NamedTuple):
    package_name: str
    version: Optional[str]
    build: Optional[str]
    package: Optional[str]

    @classmethod
    def create(
        cls, package_name: str, version: Optional[str] = None, build: Optional[str] = None, tag: Optional[str] = None
    ) -> Target:
        """Use supplied arguments to build a :class:`Target` object."""
        if tag is not None:
            assert version is None
            assert build is None
            version, build = tag.rsplit("--", 1)

        # conda package and quay image names are lowercase
        return Target(package_name=package_name.lower(), version=version, build=build, package=package_name)


class MulledImageNameGenerator:
    """
    Define a service class for generating BioContainers version 2 mulled image names.

    Adapted from https://gist.github.com/natefoo/19cefeedd1942c30f9d88027a61b3f83.

    """

    _split_pattern = re.compile(r"==?")

    @classmethod
    def parse_targets(cls, specifications: Iterable[str]) -> List[Tuple[str, str]]:
        """
        Parse tool, version pairs from specification strings.

        Args:
            specifications: An iterable of strings that contain tools and their versions.

        """
        result: List[Tuple[str, str]] = []
        for spec in specifications:
            try:
                tool, version = cls._split_pattern.split(spec, maxsplit=1)
            except ValueError:
                raise ValueError(
                    f"The specification {spec} does not have the expected format <tool==version> or <tool=version>."
                ) from None
            try:
                Version(version)
            except InvalidVersion:
                raise ValueError(f"Not a PEP440 version spec: '{version}' in '{spec}'") from None
            result.append((tool.strip(), version.strip()))
        return result

    @classmethod
    def generate_image_name(cls, targets: List[Tuple[str, str]], build_number: int = 0) -> str:
        """
        Generate the name of a BioContainers mulled image version 2.

        Args:
            targets: One or more target packages of the multi-tool container image.
            build_number: The build number for this image. This is an incremental value that starts at zero.

        """
        return cls._v2_image_name(
            [Target.create(name, version) for name, version in targets], image_build=str(build_number)
        )

    @classmethod
    def image_exists(cls, image_name: str) -> bool:
        """Check whether a given BioContainers image name exists via a call to the quay.io API."""
        quay_url = f"https://quay.io/biocontainers/{image_name}/"
        response = requests.get(quay_url, allow_redirects=True)
        log.debug(f"Got response code '{response.status_code}' for URL {quay_url}")
        if response.status_code == 200:
            log.info(f"Found [link={quay_url}]docker image[/link] on quay.io! :sparkles:")
            return True
        else:
            log.error(f"Was not able to find [link={quay_url}]docker image[/link] on quay.io")
            return False

    # Copied from galaxy.tool_util.deps.mulled.util
    @classmethod
    def _v2_image_name(
        cls, targets: List[Target], image_build: Optional[str] = None, name_override: Optional[str] = None
    ) -> str:
        """
        Generate mulled hash version 2 container identifier for supplied arguments.

        If a single target is specified, simply use the supplied name and version as
        the repository name and tag respectively. If multiple targets are supplied,
        hash the package names as the repository name and hash the package versions (if set)
        as the tag.

        >>> single_targets = [build_target("samtools", version="1.3.1")]
        >>> v2_image_name(single_targets)
        'samtools:1.3.1'
        >>> single_targets = [build_target("samtools", version="1.3.1", build="py_1")]
        >>> v2_image_name(single_targets)
        'samtools:1.3.1--py_1'
        >>> single_targets = [build_target("samtools", version="1.3.1")]
        >>> v2_image_name(single_targets, image_build="0")
        'samtools:1.3.1'
        >>> single_targets = [build_target("samtools", version="1.3.1", build="py_1")]
        >>> v2_image_name(single_targets, image_build="0")
        'samtools:1.3.1--py_1'
        >>> multi_targets = [build_target("samtools", version="1.3.1"), build_target("bwa", version="0.7.13")]
        >>> v2_image_name(multi_targets)
        'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40:4d0535c94ef45be8459f429561f0894c3fe0ebcf'
        >>> multi_targets_on_versionless = [build_target("samtools", version="1.3.1"), build_target("bwa")]
        >>> v2_image_name(multi_targets_on_versionless)
        'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40:b0c847e4fb89c343b04036e33b2daa19c4152cf5'
        >>> multi_targets_versionless = [build_target("samtools"), build_target("bwa")]
        >>> v2_image_name(multi_targets_versionless)
        'mulled-v2-fe8faa35dbf6dc65a0f7f5d4ea12e31a79f73e40'
        """
        if name_override is not None:
            print(
                "WARNING: Overriding mulled image name, auto-detection of 'mulled' package attributes will fail to detect result."
            )
            return name_override

        targets = list(targets)
        if len(targets) == 1:
            return cls._simple_image_name(targets, image_build=image_build)
        else:
            targets_order = sorted(targets, key=lambda t: t.package_name)
            package_name_buffer = "\n".join(map(lambda t: t.package_name, targets_order))
            package_hash = hashlib.sha1()
            package_hash.update(package_name_buffer.encode())

            versions = map(lambda t: t.version, targets_order)
            if any(versions):
                # Only hash versions if at least one package has versions...
                version_name_buffer = "\n".join(map(lambda t: t.version or "null", targets_order))
                version_hash = hashlib.sha1()
                version_hash.update(version_name_buffer.encode())
                version_hash_str = version_hash.hexdigest()
            else:
                version_hash_str = ""

            if not image_build:
                build_suffix = ""
            elif version_hash_str:
                # tagged verson is <version_hash>-<build>
                build_suffix = f"-{image_build}"
            else:
                # tagged version is simply the build
                build_suffix = image_build
            suffix = ""
            if version_hash_str or build_suffix:
                suffix = f":{version_hash_str}{build_suffix}"
            return f"mulled-v2-{package_hash.hexdigest()}{suffix}"

    # Copied from galaxy.tool_util.deps.mulled.util
    @classmethod
    def _simple_image_name(cls, targets: List[Target], image_build: Optional[str] = None) -> str:
        target = targets[0]
        suffix = ""
        if target.version is not None:
            build = target.build
            if build is None and image_build is not None and image_build != "0":
                # Special case image_build == "0", which has been built without a suffix
                print("WARNING: Hard-coding image build instead of using Conda build - this is not recommended.")
                build = image_build
            suffix += f":{target.version}"
            if build is not None:
                suffix += f"--{build}"
        return f"{target.package_name}{suffix}"

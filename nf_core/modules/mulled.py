"""Generate the name of a BioContainers mulled image version 2."""


import logging
import re
from packaging.version import Version, InvalidVersion
from typing import Iterable, Tuple, List

from galaxy.tool_util.deps.mulled.util import build_target, v2_image_name


log = logging.getLogger(__name__)


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
        result = []
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
                raise ValueError(f"{version} in {spec} is not a PEP440 compliant version specification.") from None
            result.append((tool.strip(), version.strip()))
        return result

    @classmethod
    def generate_image_name(cls, targets: Iterable[Tuple[str, str]]) -> str:
        """
        Generate the name of a BioContainers mulled image version 2.

        Args:
            targets: One or more tool, version pairs of the multi-tool container image.

        """
        return v2_image_name([build_target(name, version) for name, version in targets])

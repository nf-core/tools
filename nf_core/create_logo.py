import logging
from pathlib import Path
from typing import Union

import svgutils.compose as sc
import svgutils.transform as sg
from cairosvg import svg2png
from PIL import ImageFont

log = logging.getLogger(__name__)


class Logo:
    """Create a logo for a pipeline."""

    def __init__(self, no_prompts: bool = False):
        self.no_prompts = no_prompts

    def create(
        self: object,
        text: str,
        dir: Union[Path, str],
        theme: str = "light",
        width: int = 2300,
        format: str = "svg",
        force: bool = False,
    ) -> Path:
        """Create a logo for a pipeline."""

        if not text:
            raise UserWarning("Please provide the name of the text to put on the logo.")
        dir = Path(dir)
        if not dir.is_dir():
            log.debug(f"Creating directory {dir}")
            dir.mkdir(parents=True, exist_ok=True)
        logo_filename = f"nfcore-{text}_logo_{theme}.{format}"
        logo_path = Path(dir, logo_filename)

        if theme == "dark":
            template_fn = "assets/logo/nf-core-repo-logo-base-darkbg.svg"
        else:
            template_fn = "assets/logo/nf-core-repo-logo-base-lightbg.svg"

        # Check if we haven't already created this logo
        if logo_path.is_file() and not force:
            log.info(f"Logo already exists at: {logo_path}. Use `--force` to overwrite.")
            return logo_path

        log.debug(f"Creating logo for {text}")

        # make sure the figure fits the text
        font_file = ImageFont.truetype("assets/logo/MavenPro-Bold.ttf", 400)
        text_length = font_file.getmask(text).getbbox()[2]  # get the width of the text based on the font

        max_width = max(
            2300, text_length + len(text) * 20
        )  # need to add some more space to the text length to make sure it fits
        # Set size
        fig = sg.SVGFigure([str(max_width), str(1000)])

        # Load the template
        template = sg.fromfile(template_fn)

        # Get the text element
        root = template.getroot()

        font_color = theme == "light" and "rgb(5,5,5)" or "rgb(250,250,250)"

        logo = sg.TextElement(
            110,
            850,
            text,
            size=400,
            font="MavenPro-Bold",
            color=font_color,
        )

        # Add the text to the template
        fig.append([logo, root])

        # resize to given width
        fig = sc.Figure(
            str(width), str(1000 * (width / max_width)), fig.getroot().scale(width / max_width, width / max_width)
        )
        # remove the xml header (otherwise affinity designer won't open the svg)
        fig = fig.tostr().decode("utf-8").replace("<?xml version='1.0' encoding='ASCII' standalone='yes'?>\n", "")

        # Save svg
        if format == "svg":
            with open(logo_path, "w") as fh:
                fh.write(fig)
            log.debug(f"Saved logo to {logo_path}")
        elif format == "png":
            # Save png
            svg2png(bytestring=fig.encode("utf-8"), write_to=str(logo_path))
            log.debug(f"Saved logo to {logo_path}")
        else:
            raise ValueError(f"Unknown format {format}")

        # Return the logo
        return logo_path

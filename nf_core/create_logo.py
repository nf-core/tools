import logging
from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont

import nf_core

log = logging.getLogger(__name__)


def create_logo(
    text: str,
    dir: Union[Path, str],
    filename: str = "",
    theme: str = "light",
    width: int = 2300,
    force: bool = False,
) -> Path:
    """Create a logo for a pipeline."""

    if not text:
        raise UserWarning("Please provide the name of the text to put on the logo.")
    dir = Path(dir)
    if not dir.is_dir():
        log.debug(f"Creating directory {dir}")
        dir.mkdir(parents=True, exist_ok=True)
    logo_filename = f"{text}_logo_{theme}.png" if not filename else filename
    logo_filename = f"{logo_filename}.png" if not logo_filename.endswith(".png") else logo_filename
    logo_path = Path(dir, logo_filename)

    # Check if we haven't already created this logo
    if logo_path.is_file() and not force:
        log.info(f"Logo already exists at: {logo_path}. Use `--force` to overwrite.")
        return logo_path

    assets = Path(nf_core.__file__).parent / "assets/logo"
    log.debug(f"Creating logo for {text}")

    # make sure the figure fits the text
    font_path = assets / "MavenPro-Bold.ttf"
    log.debug(f"Using font: {str(font_path)}")
    font = ImageFont.truetype(str(font_path), 400)
    text_length = font.getmask(text).getbbox()[2]  # get the width of the text based on the font

    max_width = max(
        2300, text_length + len(text) * 20
    )  # need to add some more space to the text length to make sure it fits

    template_fn = "nf-core-repo-logo-base-lightbg.png"
    if theme == "dark":
        template_fn = "nf-core-repo-logo-base-darkbg.png"

    template_path = assets / template_fn
    img = Image.open(str(template_path))
    # get the height of the template image
    height = img.size[1]

    # Draw text
    draw = ImageDraw.Draw(img)
    color = theme == "dark" and (250, 250, 250) or (5, 5, 5)
    draw.text((110, 465), text, color, font=font)

    # Crop to max width
    img = img.crop((0, 0, max_width, height))

    # Resize
    img = img.resize((width, int((width / max_width) * height)))
    # Save
    img.save(logo_path, "PNG")
    log.debug(f"Saved logo to: {logo_path}")

    # Return the logo
    return logo_path

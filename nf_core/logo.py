import logging
from pathlib import Path

from drawsvg import Drawing
from rich.prompt import Prompt

from nf_core.utils import setup_nfcore_cachedir

log = logging.getLogger(__name__)


class Logo:
    """Create a logo for a pipeline."""

    def __init__(self, name: str, no_prompts=False):
        self.name = name
        self.no_prompts = no_prompts

    def create(self, text: str = "", theme="light", width=600, force=False) -> Path:
        force = self.no_prompts or force
        if not text and not self.name:
            if self.no_prompts:
                raise UserWarning("Please provide the name of the pipeline to create a logo.")
            else:
                Prompt.ask(
                    "Please provide the name of the pipeline to create a logo for:",
                    default=self.name,
                )
        else:
            text = self.name
        cache_dir = setup_nfcore_cachedir("logos")
        cache_filename = f"nfcore-{text}_logo_{theme}.svg"
        if width:
            cache_filename = f"nfcore-{text}_logo_w{width}_{theme}.svg"
        logo_cache_fn = Path(cache_dir, cache_filename)

        if theme == "dark":
            template_fn = "assets/logo/nf-core-repo-logo-base-darkbg.svg"
        else:
            template_fn = "assets/logo/nf-core-repo-logo-base-lightbg.svg"

        template_font = "assets/logo/MavenPro-Bold.ttf"
        # Check if we already have a logo cached
        if logo_cache_fn.is_file() and not force:
            log.debug(f"Using cached logo: {logo_cache_fn}")
            return logo_cache_fn

        # Create the logo
        log.debug(f"Creating logo for {text}")

        # Load the template
        drawing = Drawing(height=600, width=600)

        with open(template_fn) as fh:
            template = fh.read()

        # Add the template
        drawing.draw(template)

        # # Add the text with MavenPro-Bold font
        # drawing.embed_google_font("Maven Pro", text=set(text))

        # drawing.append(
        #     Text(text, 35, 10, 10, center=True,
        #         font_family='Maven Pro', font_style='bold')
        # )

        # Save the logo
        drawing.save_svg(logo_cache_fn)
        log.debug(f"Saved logo to {logo_cache_fn}")

        # Return the logo
        return logo_cache_fn

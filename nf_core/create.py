#!/usr/bin/env python
"""Creates a nf-core pipeline matching the current
organization's specification based on a template.
"""
from genericpath import exists
import git
import jinja2
import logging
import os
import pathlib
import requests
import shutil
import sys

import nf_core

log = logging.getLogger(__name__)


class PipelineCreate(object):
    """Creates a nf-core pipeline a la carte from the nf-core best-practice template.

    Args:
        name (str): Name for the pipeline.
        description (str): Description for the pipeline.
        author (str): Authors name of the pipeline.
        version (str): Version flag. Semantic versioning only. Defaults to `1.0dev`.
        no_git (bool): Prevents the creation of a local Git repository for the pipeline. Defaults to False.
        force (bool): Overwrites a given workflow directory with the same name. Defaults to False.
            May the force be with you.
        outdir (str): Path to the local output directory.
    """

    def __init__(self, name, description, author, version="1.0dev", no_git=False, force=False, outdir=None):
        self.short_name = name.lower().replace(r"/\s+/", "-").replace("nf-core/", "").replace("/", "-")
        self.name = f"nf-core/{self.short_name}"
        self.name_noslash = self.name.replace("/", "-")
        self.name_docker = self.name.replace("nf-core", "nfcore")
        self.description = description
        self.author = author
        self.version = version
        self.no_git = no_git
        self.force = force
        self.outdir = outdir
        if not self.outdir:
            self.outdir = os.path.join(os.getcwd(), self.name_noslash)

    def init_pipeline(self):
        """Creates the nf-core pipeline."""

        # Make the new pipeline
        self.render_template()

        # Init the git repository and make the first commit
        if not self.no_git:
            self.git_init_pipeline()

        log.info(
            "[green bold]!!!!!! IMPORTANT !!!!!!\n\n"
            + "[green not bold]If you are interested in adding your pipeline to the nf-core community,\n"
            + "PLEASE COME AND TALK TO US IN THE NF-CORE SLACK BEFORE WRITING ANY CODE!\n\n"
            + "[default]Please read: [link=https://nf-co.re/developers/adding_pipelines#join-the-community]https://nf-co.re/developers/adding_pipelines#join-the-community[/link]"
        )

    def render_template(self):
        """Runs Jinja to create a new nf-core pipeline."""
        log.info(f"Creating new nf-core pipeline: '{self.name}'")

        # Check if the output directory exists
        if os.path.exists(self.outdir):
            if self.force:
                log.warning(f"Output directory '{self.outdir}' exists - continuing as --force specified")
            else:
                log.error(f"Output directory '{self.outdir}' exists!")
                log.info("Use -f / --force to overwrite existing files")
                sys.exit(1)
        else:
            os.makedirs(self.outdir)

        # Run jinja2 for each file in the template folder
        env = jinja2.Environment(
            loader=jinja2.PackageLoader("nf_core", "pipeline-template"), keep_trailing_newline=True
        )
        template_dir = os.path.join(os.path.dirname(__file__), "pipeline-template")
        object_attrs = vars(self)
        object_attrs["nf_core_version"] = nf_core.__version__

        # Can't use glob.glob() as need recursive hidden dotfiles - https://stackoverflow.com/a/58126417/713980
        template_files = list(pathlib.Path(template_dir).glob("**/*"))
        template_files += list(pathlib.Path(template_dir).glob("*"))
        ignore_strs = [".pyc", "__pycache__", ".pyo", ".pyd", ".DS_Store", ".egg"]
        rename_files = {
            "workflows/pipeline.nf": f"workflows/{self.short_name}.nf",
            "lib/WorkflowPipeline.groovy": f"lib/Workflow{self.short_name[0].upper()}{self.short_name[1:]}.groovy",
        }

        for template_fn_path_obj in template_files:

            template_fn_path = str(template_fn_path_obj)
            if os.path.isdir(template_fn_path):
                continue
            if any([s in template_fn_path for s in ignore_strs]):
                log.debug(f"Ignoring '{template_fn_path}' in jinja2 template creation")
                continue

            # Set up vars and directories
            template_fn = os.path.relpath(template_fn_path, template_dir)
            output_path = os.path.join(self.outdir, template_fn)
            if template_fn in rename_files:
                output_path = os.path.join(self.outdir, rename_files[template_fn])
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            try:
                # Just copy binary files
                if nf_core.utils.is_file_binary(template_fn_path):
                    raise AttributeError(f"Binary file: {template_fn_path}")

                # Got this far - render the template
                log.debug(f"Rendering template file: '{template_fn}'")
                j_template = env.get_template(template_fn)
                rendered_output = j_template.render(object_attrs)

                # Write to the pipeline output file
                with open(output_path, "w") as fh:
                    log.debug(f"Writing to output file: '{output_path}'")
                    fh.write(rendered_output)

            # Copy the file directly instead of using Jinja
            except (AttributeError, UnicodeDecodeError) as e:
                log.debug(f"Copying file without Jinja: '{output_path}' - {e}")
                shutil.copy(template_fn_path, output_path)

            # Something else went wrong
            except Exception as e:
                log.error(f"Copying raw file as error rendering with Jinja: '{output_path}' - {e}")
                shutil.copy(template_fn_path, output_path)

            # Mirror file permissions
            template_stat = os.stat(template_fn_path)
            os.chmod(output_path, template_stat.st_mode)

        # Make a logo and save it
        self.make_pipeline_logo()

    def make_pipeline_logo(self):
        """Fetch a logo for the new pipeline from the nf-core website"""

        logo_url = f"https://nf-co.re/logo/{self.short_name}"
        log.debug(f"Fetching logo from {logo_url}")

        email_logo_path = f"{self.outdir}/assets/{self.name_noslash}_logo.png"
        os.makedirs(os.path.dirname(email_logo_path), exist_ok=True)
        log.debug(f"Writing logo to '{email_logo_path}'")
        r = requests.get(f"{logo_url}?w=400")
        with open(email_logo_path, "wb") as fh:
            fh.write(r.content)

        readme_logo_path = f"{self.outdir}/docs/images/{self.name_noslash}_logo.png"

        log.debug(f"Writing logo to '{readme_logo_path}'")
        os.makedirs(os.path.dirname(readme_logo_path), exist_ok=True)
        r = requests.get(f"{logo_url}?w=600")
        with open(readme_logo_path, "wb") as fh:
            fh.write(r.content)

    def git_init_pipeline(self):
        """Initialises the new pipeline as a Git repository and submits first commit."""
        log.info("Initialising pipeline git repository")
        repo = git.Repo.init(self.outdir)
        repo.git.add(A=True)
        repo.index.commit(f"initial template build from nf-core/tools, version {nf_core.__version__}")
        # Add TEMPLATE branch to git repository
        repo.git.branch("TEMPLATE")
        repo.git.branch("dev")
        log.info(
            "Done. Remember to add a remote and push to GitHub:\n"
            f"[white on grey23] cd {self.outdir} \n"
            " git remote add origin git@github.com:USERNAME/REPO_NAME.git \n"
            " git push --all origin                                       "
        )
        log.info("This will also push your newly created dev branch and the TEMPLATE branch for syncing.")

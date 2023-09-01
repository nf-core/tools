"""Creates a nf-core pipeline matching the current
organization's specification based on a template.
"""
import configparser
import logging
import os
import random
import re
import shutil
import sys
import time
from pathlib import Path

import filetype
import git
import jinja2
import questionary
import requests
import yaml

import nf_core
import nf_core.schema
import nf_core.utils
from nf_core.lint_utils import run_prettier_on_file
from nf_core.pipelines.create.utils import CreateConfig

log = logging.getLogger(__name__)


class PipelineCreate:
    """Creates a nf-core pipeline a la carte from the nf-core best-practice template.

    Args:
        name (str): Name for the pipeline.
        description (str): Description for the pipeline.
        author (str): Authors name of the pipeline.
        version (str): Version flag. Semantic versioning only. Defaults to `1.0dev`.
        no_git (bool): Prevents the creation of a local Git repository for the pipeline. Defaults to False.
        force (bool): Overwrites a given workflow directory with the same name. Defaults to False. Used for tests and sync command.
            May the force be with you.
        outdir (str): Path to the local output directory.
        template_config (str|CreateConfig): Path to template.yml file for pipeline creation settings. or pydantic model with the customisation for pipeline creation settings.
        organisation (str): Name of the GitHub organisation to create the pipeline. Will be the prefix of the pipeline.
        from_config_file (bool): If true the pipeline will be created from the `.nf-core.yml` config file. Used for tests and sync command.
        default_branch (str): Specifies the --initial-branch name.
    """

    def __init__(
        self,
        name,
        description,
        author,
        version="1.0dev",
        no_git=False,
        force=False,
        outdir=None,
        template_config=None,
        organisation="nf-core",
        from_config_file=False,
        default_branch=None,
    ):
        if template_config is not None and isinstance(template_config, str):
            # Obtain a CreateConfig object from the template yaml file
            self.config = self.check_template_yaml_info(template_config, name, description, author)
            self.update_config(organisation, version, force, outdir if outdir else ".")
        elif isinstance(template_config, CreateConfig):
            self.config = template_config
        elif from_config_file:
            # Try reading config file
            _, config_yml = nf_core.utils.load_tools_config(outdir if outdir else ".")
            # Obtain a CreateConfig object from `.nf-core.yml` config file
            if "template" in config_yml:
                self.config = CreateConfig(**config_yml["template"])
        else:
            raise UserWarning("The template configuration was not provided.")

        self.jinja_params, skip_paths = self.obtain_jinja_params_dict(
            self.config.skip_features, outdir if outdir else "."
        )

        skippable_paths = {
            "github": [
                ".github/",
                ".gitignore",
            ],
            "ci": [".github/workflows/"],
            "igenomes": ["conf/igenomes.config"],
            "is_nfcore": [
                ".github/ISSUE_TEMPLATE/config",
                "CODE_OF_CONDUCT.md",
                ".github/workflows/awsfulltest.yml",
                ".github/workflows/awstest.yml",
            ],
        }
        # Get list of files we're skipping with the supplied skip keys
        self.skip_paths = set(sp for k in skip_paths for sp in skippable_paths[k])

        # Set convenience variables
        self.name = self.config.name

        # Set fields used by the class methods
        self.no_git = no_git
        self.default_branch = default_branch
        self.force = self.config.force
        if outdir is None:
            outdir = os.path.join(os.getcwd(), self.jinja_params["name_noslash"])
        self.outdir = Path(outdir)

    def check_template_yaml_info(self, template_yaml, name, description, author):
        """Ensure that the provided template yaml file contains the necessary information.

        Args:
            template_yaml (str): Template yaml file.
            name (str): Name for the pipeline.
            description (str): Description for the pipeline.
            author (str): Authors name of the pipeline.

        Returns:
            CreateConfig: Pydantic model for the nf-core create config.

        Raises:
            UserWarning: if template yaml file does not contain all the necessary information.
            UserWarning: if template yaml file does not exist.
        """
        # Obtain template customization info from template yaml file or `.nf-core.yml` config file
        try:
            with open(template_yaml, "r") as f:
                template_yaml = yaml.safe_load(f)
                config = CreateConfig(**template_yaml)
        except FileNotFoundError:
            raise UserWarning(f"Template YAML file '{template_yaml}' not found.")

        missing_fields = []
        if config.name is None and name is None:
            missing_fields.append("name")
        elif config.name is None:
            config.name = name
        if config.description is None and description is None:
            missing_fields.append("description")
        elif config.description is None:
            config.description = description
        if config.author is None and author is None:
            missing_fields.append("author")
        elif config.author is None:
            config.author = author
        if len(missing_fields) > 0:
            raise UserWarning(
                f"Template YAML file does not contain the following required fields: {', '.join(missing_fields)}"
            )

        return config

    def update_config(self, organisation, version, force, pipeline_dir):
        """Updates the config file with arguments provided through command line.

        Args:
            organisation (str): Name of the GitHub organisation to create the pipeline.
            version (str): Version of the pipeline.
            force (bool): Overwrites a given workflow directory with the same name.
            pipeline_dir (str): Path to the local output directory.
        """
        if self.config.org is None:
            self.config.org = organisation
        if self.config.version is None:
            self.config.version = version if version else "1.0dev"
        if self.config.force is None:
            self.config.force = force if force else False
        if self.config.outdir is None:
            self.config.outdir = pipeline_dir
        if self.config.is_nfcore is None:
            self.config.is_nfcore = True if organisation == "nf-core" else False

    def obtain_jinja_params_dict(self, features_to_skip, pipeline_dir):
        """Creates a dictionary of parameters for the new pipeline.

        Args:
            features_to_skip (list<str>): List of template features/areas to skip.
            pipeline_dir (str): Path to the pipeline directory.

        Returns:
            jinja_params (dict): Dictionary of template areas to skip with values true/false.
            skip_paths (list<str>): List of template areas which contain paths to skip.
        """
        # Try reading config file
        _, config_yml = nf_core.utils.load_tools_config(pipeline_dir)

        # Define the different template areas, and what actions to take for each
        # if they are skipped
        template_areas = {
            "github": {"file": True, "content": False},
            "ci": {"file": True, "content": False},
            "github_badges": {"file": False, "content": True},
            "igenomes": {"file": True, "content": True},
            "nf_core_configs": {"file": False, "content": True},
        }

        # Set the parameters for the jinja template
        jinja_params = self.config.model_dump()

        # Add template areas to jinja params and create list of areas with paths to skip
        skip_paths = []
        for t_area in template_areas:
            if t_area in features_to_skip:
                if template_areas[t_area]["file"]:
                    skip_paths.append(t_area)
                jinja_params[t_area] = False
            else:
                jinja_params[t_area] = True

        # If github is selected, exclude also github_badges
        # if not param_dict["github"]:
        #    param_dict["github_badges"] = False

        # Set the last parameters based on the ones provided
        jinja_params["short_name"] = (
            jinja_params["name"].lower().replace(r"/\s+/", "-").replace(f"{jinja_params['org']}/", "").replace("/", "-")
        )
        jinja_params["name"] = f"{jinja_params['org']}/{jinja_params['short_name']}"
        jinja_params["name_noslash"] = jinja_params["name"].replace("/", "-")
        jinja_params["prefix_nodash"] = jinja_params["org"].replace("-", "")
        jinja_params["name_docker"] = jinja_params["name"].replace(jinja_params["org"], jinja_params["prefix_nodash"])
        jinja_params["logo_light"] = f"{jinja_params['name_noslash']}_logo_light.png"
        jinja_params["logo_dark"] = f"{jinja_params['name_noslash']}_logo_dark.png"

        if (
            "lint" in config_yml
            and "nextflow_config" in config_yml["lint"]
            and "manifest.name" in config_yml["lint"]["nextflow_config"]
        ):
            return jinja_params, skip_paths

        # Check that the pipeline name matches the requirements
        if not re.match(r"^[a-z]+$", jinja_params["short_name"]):
            if jinja_params["is_nfcore"]:
                raise UserWarning("[red]Invalid workflow name: must be lowercase without punctuation.")
            else:
                log.warning(
                    "Your workflow name is not lowercase without punctuation. This may cause Nextflow errors.\nConsider changing the name to avoid special characters."
                )

        return jinja_params, skip_paths

    def init_pipeline(self):
        """Creates the nf-core pipeline."""

        # Make the new pipeline
        self.render_template()

        # Init the git repository and make the first commit
        if not self.no_git:
            self.git_init_pipeline()

        if self.config.is_nfcore:
            log.info(
                "[green bold]!!!!!! IMPORTANT !!!!!!\n\n"
                "[green not bold]If you are interested in adding your pipeline to the nf-core community,\n"
                "PLEASE COME AND TALK TO US IN THE NF-CORE SLACK BEFORE WRITING ANY CODE!\n\n"
                "[default]Please read: [link=https://nf-co.re/developers/adding_pipelines#join-the-community]"
                "https://nf-co.re/developers/adding_pipelines#join-the-community[/link]"
            )

    def render_template(self):
        """Runs Jinja to create a new nf-core pipeline."""
        log.info(f"Creating new nf-core pipeline: '{self.name}'")

        # Check if the output directory exists
        if self.outdir.exists():
            if self.force:
                log.warning(
                    f"Output directory '{self.outdir}' exists - removing the existing directory as --force specified"
                )
                shutil.rmtree(self.outdir)
            else:
                log.error(f"Output directory '{self.outdir}' exists!")
                log.info("Use -f / --force to overwrite existing files")
                sys.exit(1)
        os.makedirs(self.outdir)

        # Run jinja2 for each file in the template folder
        env = jinja2.Environment(
            loader=jinja2.PackageLoader("nf_core", "pipeline-template"), keep_trailing_newline=True
        )
        template_dir = os.path.join(os.path.dirname(__file__), "pipeline-template")
        object_attrs = self.jinja_params
        object_attrs["nf_core_version"] = nf_core.__version__

        # Can't use glob.glob() as need recursive hidden dotfiles - https://stackoverflow.com/a/58126417/713980
        template_files = list(Path(template_dir).glob("**/*"))
        template_files += list(Path(template_dir).glob("*"))
        ignore_strs = [".pyc", "__pycache__", ".pyo", ".pyd", ".DS_Store", ".egg"]
        short_name = self.jinja_params["short_name"]
        rename_files = {
            "workflows/pipeline.nf": f"workflows/{short_name}.nf",
            "lib/WorkflowPipeline.groovy": f"lib/Workflow{short_name.title()}.groovy",
        }

        # Set the paths to skip according to customization
        for template_fn_path_obj in template_files:
            template_fn_path = str(template_fn_path_obj)

            # Skip files that are in the self.skip_paths list
            for skip_path in self.skip_paths:
                if os.path.relpath(template_fn_path, template_dir).startswith(skip_path):
                    break
            else:
                if os.path.isdir(template_fn_path):
                    continue
                if any([s in template_fn_path for s in ignore_strs]):
                    log.debug(f"Ignoring '{template_fn_path}' in jinja2 template creation")
                    continue

                # Set up vars and directories
                template_fn = os.path.relpath(template_fn_path, template_dir)
                output_path = self.outdir / template_fn
                if template_fn in rename_files:
                    output_path = self.outdir / rename_files[template_fn]
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

        # Remove all unused parameters in the nextflow schema
        if not self.jinja_params["igenomes"] or not self.jinja_params["nf_core_configs"]:
            self.update_nextflow_schema()

        if self.config.is_nfcore:
            # Make a logo and save it, if it is a nf-core pipeline
            self.make_pipeline_logo()
        else:
            if self.jinja_params["github"]:
                # Remove field mentioning nf-core docs
                # in the github bug report template
                self.remove_nf_core_in_bug_report_template()

            # Update the .nf-core.yml with linting configurations
            self.fix_linting()

        if self.config:
            config_fn, config_yml = nf_core.utils.load_tools_config(self.outdir)
            with open(self.outdir / config_fn, "w") as fh:
                config_yml.update(template=self.config.model_dump())
                yaml.safe_dump(config_yml, fh)
                log.debug(f"Dumping pipeline template yml to pipeline config file '{config_fn.name}'")
                run_prettier_on_file(self.outdir / config_fn)

    def update_nextflow_schema(self):
        """
        Removes unused parameters from the nextflow schema.
        """
        schema_path = self.outdir / "nextflow_schema.json"

        schema = nf_core.schema.PipelineSchema()
        schema.schema_filename = schema_path
        schema.no_prompts = True
        schema.load_schema()
        schema.get_wf_params()
        schema.remove_schema_notfound_configs()
        schema.save_schema(suppress_logging=True)
        run_prettier_on_file(schema_path)

    def remove_nf_core_in_bug_report_template(self):
        """
        Remove the field mentioning nf-core documentation
        in the github bug report template
        """
        bug_report_path = self.outdir / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"

        with open(bug_report_path, "r") as fh:
            contents = yaml.load(fh, Loader=yaml.FullLoader)

        # Remove the first item in the body, which is the information about the docs
        contents["body"].pop(0)

        with open(bug_report_path, "w") as fh:
            yaml.dump(contents, fh, default_flow_style=False, sort_keys=False)

        run_prettier_on_file(bug_report_path)

    def fix_linting(self):
        """
        Updates the .nf-core.yml with linting configurations
        for a customized pipeline.
        """
        # Create a lint config
        short_name = self.jinja_params["short_name"]
        lint_config = {
            "files_exist": [
                "CODE_OF_CONDUCT.md",
                f"assets/nf-core-{short_name}_logo_light.png",
                f"docs/images/nf-core-{short_name}_logo_light.png",
                f"docs/images/nf-core-{short_name}_logo_dark.png",
                ".github/ISSUE_TEMPLATE/config.yml",
                ".github/workflows/awstest.yml",
                ".github/workflows/awsfulltest.yml",
            ],
            "files_unchanged": [
                "CODE_OF_CONDUCT.md",
                f"assets/nf-core-{short_name}_logo_light.png",
                f"docs/images/nf-core-{short_name}_logo_light.png",
                f"docs/images/nf-core-{short_name}_logo_dark.png",
            ],
            "nextflow_config": [
                "manifest.name",
                "manifest.homePage",
            ],
            "multiqc_config": ["report_comment"],
        }

        # Add GitHub hosting specific configurations
        if not self.jinja_params["github"]:
            lint_config["files_exist"].extend(
                [
                    ".github/ISSUE_TEMPLATE/bug_report.yml",
                    ".github/ISSUE_TEMPLATE/feature_request.yml",
                    ".github/PULL_REQUEST_TEMPLATE.md",
                    ".github/CONTRIBUTING.md",
                    ".github/.dockstore.yml",
                    ".gitignore",
                ]
            )
            lint_config["files_unchanged"].extend(
                [
                    ".github/ISSUE_TEMPLATE/bug_report.yml",
                    ".github/ISSUE_TEMPLATE/config.yml",
                    ".github/ISSUE_TEMPLATE/feature_request.yml",
                    ".github/PULL_REQUEST_TEMPLATE.md",
                    ".github/workflows/branch.yml",
                    ".github/workflows/linting_comment.yml",
                    ".github/workflows/linting.yml",
                    ".github/CONTRIBUTING.md",
                    ".github/.dockstore.yml",
                ]
            )

        # Add CI specific configurations
        if not self.jinja_params["ci"]:
            lint_config["files_exist"].extend(
                [
                    ".github/workflows/branch.yml",
                    ".github/workflows/ci.yml",
                    ".github/workflows/linting_comment.yml",
                    ".github/workflows/linting.yml",
                ]
            )

        # Add custom config specific configurations
        if not self.jinja_params["nf_core_configs"]:
            lint_config["files_exist"].extend(["conf/igenomes.config"])
            lint_config["nextflow_config"].extend(
                [
                    "process.cpus",
                    "process.memory",
                    "process.time",
                    "custom_config",
                ]
            )

        # Add igenomes specific configurations
        if not self.jinja_params["igenomes"]:
            lint_config["files_exist"].extend(["conf/igenomes.config"])

        # Add github badges specific configurations
        if not self.jinja_params["github_badges"] or not self.jinja_params["github"]:
            lint_config["readme"] = ["nextflow_badge"]

        # If the pipeline is not nf-core
        if not self.config.is_nfcore:
            lint_config["files_unchanged"].extend([".github/ISSUE_TEMPLATE/bug_report.yml"])

        # Add the lint content to the preexisting nf-core config
        config_fn, nf_core_yml = nf_core.utils.load_tools_config(self.outdir)
        nf_core_yml["lint"] = lint_config
        with open(self.outdir / config_fn, "w") as fh:
            yaml.dump(nf_core_yml, fh, default_flow_style=False, sort_keys=False)

        run_prettier_on_file(os.path.join(self.outdir, config_fn))

    def make_pipeline_logo(self):
        """Fetch a logo for the new pipeline from the nf-core website"""

        logo_url = f"https://nf-co.re/logo/{self.jinja_params['short_name']}?theme=light"
        log.debug(f"Fetching logo from {logo_url}")

        email_logo_path = self.outdir / "assets" / f"{self.jinja_params['name_noslash']}_logo_light.png"
        self.download_pipeline_logo(f"{logo_url}?w=600&theme=light", email_logo_path)
        for theme in ["dark", "light"]:
            readme_logo_url = f"{logo_url}?w=600&theme={theme}"
            readme_logo_path = self.outdir / "docs" / "images" / f"{self.jinja_params['name_noslash']}_logo_{theme}.png"
            self.download_pipeline_logo(readme_logo_url, readme_logo_path)

    def download_pipeline_logo(self, url, img_fn):
        """Attempt to download a logo from the website. Retry if it fails."""
        os.makedirs(os.path.dirname(img_fn), exist_ok=True)
        attempt = 0
        max_attempts = 10
        retry_delay = 0  # x up to 10 each time, so first delay will be 1-100 seconds
        while attempt < max_attempts:
            # If retrying, wait a while
            if retry_delay > 0:
                log.info(f"Waiting {retry_delay} seconds before next image fetch attempt")
                time.sleep(retry_delay)

            attempt += 1
            # Use a random number to avoid the template sync hitting the website simultaneously for all pipelines
            retry_delay = random.randint(1, 100) * attempt
            log.debug(f"Fetching logo '{img_fn}' (attempt {attempt})")
            try:
                # Try to fetch the logo from the website
                r = requests.get(url, timeout=180)
                if r.status_code != 200:
                    raise UserWarning(f"Got status code {r.status_code}")
                # Check that the returned image looks right

            except (ConnectionError, UserWarning) as e:
                # Something went wrong - try again
                log.warning(e)
                log.error("Connection error - retrying")
                continue

            # Write the new logo to the file
            with open(img_fn, "wb") as fh:
                fh.write(r.content)
            # Check that the file looks valid
            image_type = filetype.guess(img_fn).extension
            if image_type != "png":
                log.error(f"Logo from the website didn't look like an image: '{image_type}'")
                continue

            # Got this far, presumably it's good - break the retry loop
            break

    def git_init_pipeline(self):
        """Initialises the new pipeline as a Git repository and submits first commit.

        Raises:
            UserWarning: if Git default branch is set to 'dev' or 'TEMPLATE'.
        """
        default_branch = self.default_branch
        try:
            default_branch = default_branch or git.config.GitConfigParser().get_value("init", "defaultBranch")
        except configparser.Error:
            log.debug("Could not read init.defaultBranch")
        if default_branch in ["dev", "TEMPLATE"]:
            raise UserWarning(
                f"Your Git defaultBranch '{default_branch}' is incompatible with nf-core.\n"
                "'dev' and 'TEMPLATE' can not be used as default branch name.\n"
                "Set the default branch name with "
                "[white on grey23] git config --global init.defaultBranch <NAME> [/]\n"
                "Or set the default_branch parameter in this class.\n"
                "Pipeline git repository will not be initialised."
            )

        log.info("Initialising pipeline git repository")
        repo = git.Repo.init(self.outdir)
        repo.git.add(A=True)
        repo.index.commit(f"initial template build from nf-core/tools, version {nf_core.__version__}")
        if default_branch:
            repo.active_branch.rename(default_branch)
        repo.git.branch("TEMPLATE")
        repo.git.branch("dev")
        log.info(
            "Done. Remember to add a remote and push to GitHub:\n"
            f"[white on grey23] cd {self.outdir} \n"
            " git remote add origin git@github.com:USERNAME/REPO_NAME.git \n"
            " git push --all origin                                       "
        )
        log.info("This will also push your newly created dev branch and the TEMPLATE branch for syncing.")

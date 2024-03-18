"""Creates a nf-core pipeline matching the current
organization's specification based on a template.
"""

import configparser
import logging
import os
import re
import shutil
import sys
from pathlib import Path

import git
import jinja2
import questionary
import yaml

import nf_core
import nf_core.schema
import nf_core.utils
from nf_core.create_logo import create_logo
from nf_core.lint_utils import run_prettier_on_file

log = logging.getLogger(__name__)


class PipelineCreate:
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
        template_yaml_path (str): Path to template.yml file for pipeline creation settings.
        plain (bool): If true the Git repository will be initialized plain.
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
        template_yaml_path=None,
        plain=False,
        default_branch=None,
    ):
        self.template_params, skip_paths_keys, self.template_yaml = self.create_param_dict(
            name, description, author, version, template_yaml_path, plain, outdir if outdir else "."
        )

        skippable_paths = {
            "github": [
                ".github/",
                ".gitignore",
            ],
            "ci": [".github/workflows/"],
            "igenomes": ["conf/igenomes.config"],
            "branded": [
                ".github/ISSUE_TEMPLATE/config",
                "CODE_OF_CONDUCT.md",
                ".github/workflows/awsfulltest.yml",
                ".github/workflows/awstest.yml",
            ],
        }
        # Get list of files we're skipping with the supplied skip keys
        self.skip_paths = set(sp for k in skip_paths_keys for sp in skippable_paths[k])

        # Set convenience variables
        self.name = self.template_params["name"]

        # Set fields used by the class methods
        self.no_git = (
            no_git if self.template_params["github"] else True
        )  # Set to True if template was configured without github hosting
        self.default_branch = default_branch
        self.force = force
        if outdir is None:
            outdir = os.path.join(os.getcwd(), self.template_params["name_noslash"])
        self.outdir = Path(outdir)

    def create_param_dict(self, name, description, author, version, template_yaml_path, plain, pipeline_dir):
        """Creates a dictionary of parameters for the new pipeline.

        Args:
            name (str): Name for the pipeline.
            description (str): Description for the pipeline.
            author (str): Authors name of the pipeline.
            version (str): Version flag.
            template_yaml_path (str): Path to YAML file containing template parameters.
            plain (bool): If true the pipeline template will be initialized plain, without customisation.
            pipeline_dir (str): Path to the pipeline directory.
        """
        # Try reading config file
        _, config_yml = nf_core.utils.load_tools_config(pipeline_dir)

        # Obtain template customization info from template yaml file or `.nf-core.yml` config file
        try:
            if template_yaml_path is not None:
                with open(template_yaml_path) as f:
                    template_yaml = yaml.safe_load(f)
            elif "template" in config_yml:
                template_yaml = config_yml["template"]
            else:
                template_yaml = {}
        except FileNotFoundError:
            raise UserWarning(f"Template YAML file '{template_yaml_path}' not found.")

        param_dict = {}
        # Get the necessary parameters either from the template or command line arguments
        param_dict["name"] = self.get_param("name", name, template_yaml, template_yaml_path)
        param_dict["description"] = self.get_param("description", description, template_yaml, template_yaml_path)
        param_dict["author"] = self.get_param("author", author, template_yaml, template_yaml_path)

        if "version" in template_yaml:
            if version is not None:
                log.info(f"Overriding --version with version found in {template_yaml_path}")
            version = template_yaml["version"]
        param_dict["version"] = version

        # Define the different template areas, and what actions to take for each
        # if they are skipped
        template_areas = {
            "github": {"name": "GitHub hosting", "file": True, "content": False},
            "ci": {"name": "GitHub CI", "file": True, "content": False},
            "github_badges": {"name": "GitHub badges", "file": False, "content": True},
            "igenomes": {"name": "iGenomes config", "file": True, "content": True},
            "nf_core_configs": {"name": "nf-core/configs", "file": False, "content": True},
        }

        # Once all necessary parameters are set, check if the user wants to customize the template more
        if template_yaml_path is None and not plain:
            customize_template = questionary.confirm(
                "Do you want to customize which parts of the template are used?",
                style=nf_core.utils.nfcore_question_style,
                default=False,
            ).unsafe_ask()
            if customize_template:
                template_yaml.update(self.customize_template(template_areas))

        # Now look in the template for more options, otherwise default to nf-core defaults
        param_dict["prefix"] = template_yaml.get("prefix", "nf-core")
        param_dict["branded"] = param_dict["prefix"] == "nf-core"

        skip_paths = [] if param_dict["branded"] else ["branded"]

        for t_area in template_areas:
            areas_to_skip = template_yaml.get("skip", [])
            if isinstance(areas_to_skip, str):
                areas_to_skip = [areas_to_skip]
            if t_area in areas_to_skip:
                if template_areas[t_area]["file"]:
                    skip_paths.append(t_area)
                param_dict[t_area] = False
            else:
                param_dict[t_area] = True
        # If github is selected, exclude also github_badges
        if not param_dict["github"]:
            param_dict["github_badges"] = False

        # Set the last parameters based on the ones provided
        param_dict["short_name"] = (
            param_dict["name"].lower().replace(r"/\s+/", "-").replace(f"{param_dict['prefix']}/", "").replace("/", "-")
        )
        param_dict["name"] = f"{param_dict['prefix']}/{param_dict['short_name']}"
        param_dict["name_noslash"] = param_dict["name"].replace("/", "-")
        param_dict["prefix_nodash"] = param_dict["prefix"].replace("-", "")
        param_dict["name_docker"] = param_dict["name"].replace(param_dict["prefix"], param_dict["prefix_nodash"])
        param_dict["logo_light"] = f"nf-core-{param_dict['short_name']}_logo_light.png"
        param_dict["logo_dark"] = f"nf-core-{param_dict['short_name']}_logo_dark.png"
        param_dict["version"] = version

        if (
            "lint" in config_yml
            and "nextflow_config" in config_yml["lint"]
            and "manifest.name" in config_yml["lint"]["nextflow_config"]
        ):
            return param_dict, skip_paths, template_yaml

        # Check that the pipeline name matches the requirements
        if not re.match(r"^[a-z]+$", param_dict["short_name"]):
            if param_dict["prefix"] == "nf-core":
                raise UserWarning("[red]Invalid workflow name: must be lowercase without punctuation.")
            else:
                log.warning(
                    "Your workflow name is not lowercase without punctuation. This may cause Nextflow errors.\nConsider changing the name to avoid special characters."
                )

        return param_dict, skip_paths, template_yaml

    def customize_template(self, template_areas):
        """Customizes the template parameters.

        Args:
            template_areas (list<str>): List of available template areas to skip.
        """
        template_yaml = {}
        prefix = questionary.text("Pipeline prefix", style=nf_core.utils.nfcore_question_style).unsafe_ask()
        while not re.match(r"^[a-zA-Z_][a-zA-Z0-9-_]*$", prefix):
            log.error("[red]Pipeline prefix cannot start with digit or hyphen and cannot contain punctuation.[/red]")
            prefix = questionary.text(
                "Please provide a new pipeline prefix", style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()
        template_yaml["prefix"] = prefix

        choices = [{"name": template_areas[area]["name"], "value": area} for area in template_areas]
        template_yaml["skip"] = questionary.checkbox(
            "Skip template areas?", choices=choices, style=nf_core.utils.nfcore_question_style
        ).unsafe_ask()
        return template_yaml

    def get_param(self, param_name, passed_value, template_yaml, template_yaml_path):
        if param_name in template_yaml:
            if passed_value is not None:
                log.info(f"overriding --{param_name} with name found in {template_yaml_path}")
            passed_value = template_yaml[param_name]
        if passed_value is None:
            passed_value = getattr(self, f"prompt_wf_{param_name}")()
        return passed_value

    def prompt_wf_name(self):
        wf_name = questionary.text("Workflow name", style=nf_core.utils.nfcore_question_style).unsafe_ask()
        while not re.match(r"^[a-z]+$", wf_name):
            log.error("[red]Invalid workflow name: must be lowercase without punctuation.")
            wf_name = questionary.text(
                "Please provide a new workflow name", style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()
        return wf_name

    def prompt_wf_description(self):
        wf_description = questionary.text("Description", style=nf_core.utils.nfcore_question_style).unsafe_ask()
        return wf_description

    def prompt_wf_author(self):
        wf_author = questionary.text("Author", style=nf_core.utils.nfcore_question_style).unsafe_ask()
        return wf_author

    def init_pipeline(self):
        """Creates the nf-core pipeline."""

        # Make the new pipeline
        self.render_template()

        # Init the git repository and make the first commit
        if not self.no_git:
            self.git_init_pipeline()

        if self.template_params["branded"]:
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
        object_attrs = self.template_params
        object_attrs["nf_core_version"] = nf_core.__version__

        # Can't use glob.glob() as need recursive hidden dotfiles - https://stackoverflow.com/a/58126417/713980
        template_files = list(Path(template_dir).glob("**/*"))
        template_files += list(Path(template_dir).glob("*"))
        ignore_strs = [".pyc", "__pycache__", ".pyo", ".pyd", ".DS_Store", ".egg"]
        short_name = self.template_params["short_name"]
        rename_files = {
            "workflows/pipeline.nf": f"workflows/{short_name}.nf",
            "subworkflows/local/utils_nfcore_pipeline_pipeline/main.nf": f"subworkflows/local/utils_nfcore_{short_name}_pipeline/main.nf",
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
        if not self.template_params["igenomes"] or not self.template_params["nf_core_configs"]:
            self.update_nextflow_schema()

        if self.template_params["branded"]:
            # Make a logo and save it, if it is a nf-core pipeline
            self.make_pipeline_logo()
        else:
            if self.template_params["github"]:
                # Remove field mentioning nf-core docs
                # in the github bug report template
                self.remove_nf_core_in_bug_report_template()

            # Update the .nf-core.yml with linting configurations
            self.fix_linting()

        if self.template_yaml:
            config_fn, config_yml = nf_core.utils.load_tools_config(self.outdir)
            with open(self.outdir / config_fn, "w") as fh:
                config_yml.update(template=self.template_yaml)
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

        with open(bug_report_path) as fh:
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
        short_name = self.template_params["short_name"]
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
        if not self.template_params["github"]:
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
        if not self.template_params["ci"]:
            lint_config["files_exist"].extend(
                [
                    ".github/workflows/branch.yml",
                    ".github/workflows/ci.yml",
                    ".github/workflows/linting_comment.yml",
                    ".github/workflows/linting.yml",
                ]
            )

        # Add custom config specific configurations
        if not self.template_params["nf_core_configs"]:
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
        if not self.template_params["igenomes"]:
            lint_config["files_exist"].extend(["conf/igenomes.config"])

        # Add github badges specific configurations
        if not self.template_params["github_badges"] or not self.template_params["github"]:
            lint_config["readme"] = ["nextflow_badge"]

        # If the pipeline is unbranded
        if not self.template_params["branded"]:
            lint_config["files_unchanged"].extend([".github/ISSUE_TEMPLATE/bug_report.yml"])

        # Add the lint content to the preexisting nf-core config
        config_fn, nf_core_yml = nf_core.utils.load_tools_config(self.outdir)
        nf_core_yml["lint"] = lint_config
        with open(self.outdir / config_fn, "w") as fh:
            yaml.dump(nf_core_yml, fh, default_flow_style=False, sort_keys=False)

        run_prettier_on_file(os.path.join(self.outdir, config_fn))

    def make_pipeline_logo(self):
        """Fetch a logo for the new pipeline from the nf-core website"""
        email_logo_path = Path(self.outdir) / "assets"
        create_logo(text=self.template_params["short_name"], dir=email_logo_path, theme="light", force=self.force)
        for theme in ["dark", "light"]:
            readme_logo_path = Path(self.outdir) / "docs" / "images"
            create_logo(
                text=self.template_params["short_name"], dir=readme_logo_path, width=600, theme=theme, force=self.force
            )

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
        try:
            repo.git.branch("TEMPLATE")
            repo.git.branch("dev")

        except git.GitCommandError as e:
            if "already exists" in e.stderr:
                log.debug("Branches 'TEMPLATE' and 'dev' already exist")
                if self.force:
                    log.debug("Force option set - deleting branches")
                    repo.git.branch("-D", "TEMPLATE")
                    repo.git.branch("-D", "dev")
                    repo.git.branch("TEMPLATE")
                    repo.git.branch("dev")
                else:
                    log.error(
                        "Branches 'TEMPLATE' and 'dev' already exist. Use --force to overwrite existing branches."
                    )
                    sys.exit(1)
        log.info(
            "Done. Remember to add a remote and push to GitHub:\n"
            f"[white on grey23] cd {self.outdir} \n"
            " git remote add origin git@github.com:USERNAME/REPO_NAME.git \n"
            " git push --all origin                                       "
        )
        log.info("This will also push your newly created dev branch and the TEMPLATE branch for syncing.")

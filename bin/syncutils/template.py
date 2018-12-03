import tempfile
from syncutils import utils
import git
import os
import shutil

import nf_core.create

TEMPLATE_BRANCH = "TEMPLATE"


class NfcoreTemplate:
    """Updates the template content of an nf-core pipeline in
    its `TEMPLATE` branch.

    Args: - pipeline: The pipeline name
          - branch: The template branch name, default=`TEMPLATE`
          - token: GitHub auth token
    """
    def __init__(self, pipeline, branch=TEMPLATE_BRANCH, repo_url=""):
        """Basic constructor
        """
        self.pipeline = pipeline
        self.repo_url = repo_url
        self.branch = branch
        self.tmpdir = tempfile.mkdtemp()
        self.templatedir = tempfile.mkdtemp()
        self.repo = git.Repo.clone_from(self.repo_url, self.tmpdir)
        assert self.repo

    def sync(self):
        """Execute the template update.
        """
        context = self.context_from_nextflow(nf_project_dir=self.tmpdir)
        self.update_child_template(self.templatedir, self.tmpdir, context=context)
        self.commit_changes()
        self.push_changes()

    def context_from_nextflow(self, nf_project_dir):
        """Fetch a Nextflow pipeline's config settings.

        Returns: A cookiecutter-readable context (Python dictionary)
        """
        # Check if we are on "master" (main pipeline code)
        if self.repo.active_branch.name != "master":
            self.repo.git.checkout("origin/master", b="master")

        # Fetch the config variables from the Nextflow pipeline
        config = utils.fetch_wf_config(wf_path=nf_project_dir)

        # Checkout again to configured template branch
        self.repo.git.checkout("origin/{branch}".format(branch=self.branch),
            b="{branch}".format(branch=self.branch))

        return utils.create_context(config)

    def update_child_template(self, templatedir, target_dir, context=None):
        """Apply the changes of the cookiecutter template
        to the pipelines template branch.
        """
        # Clear the pipeline's template branch content
        for f in os.listdir(self.tmpdir):
            if f == ".git":
                continue
            try:
                shutil.rmtree(os.path.join(target_dir, f))
            except:
                os.remove(os.path.join(target_dir, f))
        print(target_dir)
        print(context.get('author'))
        # Create the new template structure
        nf_core.create.PipelineCreate(
            name=context.get('pipeline_name'),
            description=context.get('pipeline_short_description'),
            new_version=context.get('version'),
            no_git=True,
            force=True,
            outdir=target_dir,
            author=context.get('author')
        ).init_pipeline()

    def commit_changes(self):
        """Commits the changes of the new template to the current branch.
        """
        self.repo.git.add(A=True)
        self.repo.index.commit("Update nf-core pipeline template.")

    def push_changes(self):
        self.repo.git.push()

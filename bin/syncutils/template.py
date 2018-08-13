import tempfile
import utils
import git
import os
import shutil
from cookiecutter.main import cookiecutter

class NfcoreTemplate:
    """Updates the template content of an nf-core pipeline in
    its `TEMPLATE` branch.

    Args: - pipeline: The pipeline name
          - branch: The template branch name, default=`TEMPLATE`
          - token: GitHub auth token
    """
    def __init__(self, pipeline, branch='master', repo_url=""):
        """Basic constructor
        """
        self.pipeline = pipeline
        self.repo_url = repo_url
        self.branch = branch
        self.tmpdir = tempfile.mkdtemp()
        self.templatedir = tempfile.mkdtemp()
        self.repo = git.Repo.clone_from(self.repo_url, self.tmpdir)
        assert self.repo
    
    def sync(self, template_url):
        """Execute the template update.
        """
        context = self.context_from_nextflow(nf_project_dir=self.tmpdir)
        self.update_child_template(template_url, self.templatedir, self.tmpdir, context=context)
        self.commit_changes()
        self.push_changes()

    def context_from_nextflow(self, nf_project_dir):
        """Fetch a Nextflow pipeline's config settings.

        Returns: A cookiecutter-readable context (Python dictionary)
        """
        # Check if we are on "master" (main pipeline code)
        if self.repo.active_branch is not "master":
            self.repo.git.checkout("origin/master", b="master")

        # Fetch the config variables from the Nextflow pipeline
        config = utils.fetch_wf_config(wf_path=nf_project_dir)
        
        # Checkout again to configured template branch
        self.repo.git.checkout("origin/{branch}".format(branch=self.branch),
            b="{branch}".format(branch=self.branch))

        return utils.create_context(config)
    

    def update_child_template(self, template_url, templatedir, target_dir, context=None):
        """Apply the changes of the cookiecutter template
        to the pipelines template branch.
        """
        cookiecutter(template_url,
                     no_input=True,
                     extra_context=context,
                     overwrite_if_exists=True,
                     output_dir=templatedir)
        # Clear the pipeline's template branch content
        for f in os.listdir(self.tmpdir):
            if f == ".git": continue
            try:
                shutil.rmtree(os.path.join(target_dir, f))
            except:
                os.remove(os.path.join(target_dir, f))
        # Move the new template content into the template branch
        template_path = os.path.join(self.templatedir, self.pipeline)
        for f in os.listdir(template_path):
            shutil.move(
                os.path.join(template_path, f), # src
                os.path.join(self.tmpdir, f), # dest
            )

    def commit_changes(self):
        """Commits the changes of the new template to the current branch.
        """
        self.repo.git.add(A=True)
        self.repo.index.commit("Update nf-core pipeline template.")

    def push_changes(self):
        self.repo.git.push()
        
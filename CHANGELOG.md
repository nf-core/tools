# nf-core/tools: Changelog

## [v3.3.2 - Tungsten Tamarin Patch 2](https://github.com/nf-core/tools/releases/tag/3.3.2) - [2025-07-08]

### Template

- Avoid overriding `NFT_DIFF` and `NFT_DIFF_ARGS` in `nf-test` action ([#3606](https://github.com/nf-core/tools/pull/3606)) and ([#3619](https://github.com/nf-core/tools/pull/3619))
- fix nf-test scope to ignore nf-core module/swf tests ([#3609](https://github.com/nf-core/tools/pull/3609))
- write github.run_id on pipeline template ([#3637](https://github.com/nf-core/tools/pull/3637))
- Bump nf-schema to `2.4.2` ([#3533](https://github.com/nf-core/tools/pull/3533))
- Bump the minimal Nextflow version to `24.10.5` ([#3533](https://github.com/nf-core/tools/pull/3533), [#3667](https://github.com/nf-core/tools/pull/3667))
- CI - Only trigger nf-test action on pull_request ([#3628](https://github.com/nf-core/tools/pull/3628))
- Fix link to nf-test GHA in README.md ([#3630](https://github.com/nf-core/tools/pull/3630))
- Add accelerator directive for GPU-enabled processes ([#3632](https://github.com/nf-core/tools/pull/3632))
- Update dependency prettier to v3.6.0 ([#3641](https://github.com/nf-core/tools/pull/3641)) and 3.6.2 ([#3646](https://github.com/nf-core/tools/pull/3646))
- Add opt-in feature `gpu` ([#3562](https://github.com/nf-core/tools/pull/3562))
- Update zentered/bluesky-post-action action to v0.3.0 ([#3626](https://github.com/nf-core/tools/pull/3626))

### Linting

- Fix linting of nf-test files content ([#3603](https://github.com/nf-core/tools/pull/3603))

### Modules

- Remove args stub from module template to satisfy language server ([#3403](https://github.com/nf-core/tools/pull/3403))
- Fix modules meta.yml file structure ([#3532](https://github.com/nf-core/tools/pull/3532))
- Fix wrong key when updating module outputs ([#3665](https://github.com/nf-core/tools/pull/3665))

### Subworkflows

### General

- update id of ruff hook in pre-commit config ([#3621](https://github.com/nf-core/tools/pull/3621))
- Fixes a bug with the test-datasets subcommand [#3617](https://github.com/nf-core/tools/issues/3617)
- Pin python Docker tag to f2fdaec ([#3623](https://github.com/nf-core/tools/pull/3623))
- Make changelog bot push to correct remote ([#3638](https://github.com/nf-core/tools/pull/3638))
- Give unique button ids to help buttons in create app ([#3645](https://github.com/nf-core/tools/pull/3645))
- Parallelize pytest runs and speed up coverage step ([#3635](https://github.com/nf-core/tools/pull/3635))
- Update gitpod/workspace-base Docker digest to 77021d8 ([#3649](https://github.com/nf-core/tools/pull/3649))
- Update error message for rocrate_readme_sync ([#3652](https://github.com/nf-core/tools/pull/3652))
- Update `nf-core modules info` command after `meta.yml` restructuring ([#3659](https://github.com/nf-core/tools/pull/3659))
- Enable parsing of multi-line config values ([#3629](https://github.com/nf-core/tools/pull/3629))

#### Version updates

- Drop python 3.8, add tests with python 3.13 ([#3538](https://github.com/nf-core/tools/pull/3538))
- Update python:3.13-slim Docker digest to 6544e0e ([#3663](https://github.com/nf-core/tools/pull/3663))
- Update pre-commit hook astral-sh/ruff-pre-commit to v0.12.2 ([#3627](https://github.com/nf-core/tools/pull/3627),[#3648](https://github.com/nf-core/tools/pull/3648), [#3661](https://github.com/nf-core/tools/pull/3661))
- Update dependency textual to v3.5.0 ([#3636](https://github.com/nf-core/tools/pull/3636))
- Update pre-commit hook pre-commit/mirrors-mypy to v1.16.1 ([#3624](https://github.com/nf-core/tools/pull/3624))

## [v3.3.1 - Tungsten Tamarin Patch](https://github.com/nf-core/tools/releases/tag/3.3.1) - [2025-06-02]

### Template

- Use correct comment symbol in `nf-test.yml` ([#3601](https://github.com/nf-core/tools/pull/3601))

## [v3.3.0 - Tungsten Tamarin](https://github.com/nf-core/tools/releases/tag/3.3.0) - [2025-06-02]

**Highlights**

This version adds pipeline level [nf-test](https://www.nf-test.com/) to the pipeline template.
We also enabled to install subworkflows with modules from different remotes.

### Template

- Remove the on `pull_request_target` trigger and `pull_request` types from the download test. Also drop `push` triggers on other CI tests. ([#3399](https://github.com/nf-core/tools/pull/3399))
- Add nf-core template version badges to README ([#3396](https://github.com/nf-core/tools/pull/3396))
- Basic pipeline level nf-test tests ([#3469](https://github.com/nf-core/tools/pull/3469), [3597](https://github.com/nf-core/tools/pull/3597))
- Add Bluesky badge to readme ([#3475](https://github.com/nf-core/tools/pull/3475))
- Add .nftignore to trigger list ([#3508](https://github.com/nf-core/tools/pull/3508))
- Tun nf-test tests on runsOn runners ([#3525](https://github.com/nf-core/tools/pull/3525))
- Include the centralized nf-core configs also in offline mode, if a local copy is available. ([#3491](https://github.com/nf-core/tools/pull/3491))
- Make jobs automatically resubmit for exit code 175 ([#3564](https://github.com/nf-core/tools/pull/3564))
- Bump nf-schema back to 2.3.0 ([#3577](https://github.com/nf-core/tools/pull/3577))
- Do not skip AWS fulltest action on release ([#3583](https://github.com/nf-core/tools/pull/3583))
- Make all github actions in the template kebab-case ([#3600](https://github.com/nf-core/tools/pull/3600))

### Linting

- Add linting for ifEmpty(null) ([#3411](https://github.com/nf-core/tools/pull/3411))
- Fix arbitrarily nested params schema linting ([#3443](https://github.com/nf-core/tools/pull/3443))
- Fix linting with comments after the input directive ([#3458](https://github.com/nf-core/tools/pull/3458))
- EDAM ontology fixes ([#3460](https://github.com/nf-core/tools/pull/3460))
- Fix default linting of nf-core components when `nf-core pipelines lint` is ran ([#3480](https://github.com/nf-core/tools/pull/3480))
- Fix the unexpected warning and sychronize the `README.md` and `RO-crate-metadata.json` ([#3493](https://github.com/nf-core/tools/pull/3493))
- Adapt the linter to the new notation used to include the centralized nf-core configs ([#3491](https://github.com/nf-core/tools/pull/3491))
- Addressing more cases than can happen when processing input and output values ([#3541](https://github.com/nf-core/tools/pull/3541))
- Add linting of nf-test files content ([#3580](https://github.com/nf-core/tools/pull/3580))

### Subworkflows

- Install subworkflows with modules from different remotes ([#3083](https://github.com/nf-core/tools/pull/3083))

### Modules

- Increase meta index for multiple input channels ([#3463](https://github.com/nf-core/tools/pull/3463))
- Configure the default module repository, branch, and path from environment variables. ([#3481](https://github.com/nf-core/tools/pull/3481))

### General

- Remove hard coded key prefix for schema in launcher ([#3432](https://github.com/nf-core/tools/pull/3432))
- Output passed to `write_params_file` as Path object ([#3435](https://github.com/nf-core/tools/pull/3435))
- format name/value with YAML syntax ([#3442](https://github.com/nf-core/tools/pull/3442))
- Remove Twitter from README ([#3454](https://github.com/nf-core/tools/pull/3454))
- docs: fix contributing link in the main README ([#3459](https://github.com/nf-core/tools/pull/3459))
- Cleanup: Removed Redundant if Condition ([#3468](https://github.com/nf-core/tools/pull/3468))
- Ontology fix comment yaml ([#3502](https://github.com/nf-core/tools/pull/3502))
- Bugfix - add back logo to the README ([#3504](https://github.com/nf-core/tools/pull/3504))
- Update dead link ([#3505](https://github.com/nf-core/tools/pull/3505))
- Changing retrieval of file extension from EDAM ([#3512](https://github.com/nf-core/tools/pull/3512))
- Refactor adding EDAM ontologies and allowing detect more patterns (e.g., versions.yml) ([#3519](https://github.com/nf-core/tools/pull/3519))
- Add offline configs test action ([#3524](https://github.com/nf-core/tools/pull/3524))
- Adds `test-datasets` subcommand for listing/searching files in the nf-core/test-datasets repo from the cli ([#3487](https://github.com/nf-core/tools/issues/3487), [#3548](https://github.com/nf-core/tools/pull/3548), [#3566](https://github.com/nf-core/tools/pull/3566), [#3567](https://github.com/nf-core/tools/pull/3567))
- Fix indentation in included_configs API docs ([#3523](https://github.com/nf-core/tools/pull/3523))
- Adding boundary in regex ([#3535](https://github.com/nf-core/tools/pull/3535))
- Switch to using runsOn runners in nf-core/tools repo ([#3537](https://github.com/nf-core/tools/pull/3537))
- Handling issue with arity #3530 ([#3539](https://github.com/nf-core/tools/pull/3539))
- GitHub action for nightly tests with Nextflow from source ([#3553](https://github.com/nf-core/tools/pull/3553))
- Update CI to test template pipelines with nf-test ([#3559](https://github.com/nf-core/tools/pull/3559))
- Use secret for notification email on nextflow nightly builds ([#3576](https://github.com/nf-core/tools/pull/3576))
- Use pdiff from setup-nf-test ([#3578](https://github.com/nf-core/tools/pull/3578))

#### Version updates

- chore(deps): update python:3.12-slim docker digest to fd95fa2 ([#3587](https://github.com/nf-core/tools/pull/3587))
- chore(deps): update dependency pytest-textual-snapshot to v1.1.0 ([#3439](https://github.com/nf-core/tools/pull/3439))
- chore(deps): update pre-commit hook astral-sh/ruff-pre-commit to v0.11.11 ([#3585](https://github.com/nf-core/tools/pull/3585))
- chore(deps): update pre-commit hook editorconfig-checker/editorconfig-checker.python to v3.2.0 ([#3446](https://github.com/nf-core/tools/pull/3446))
- chore(deps): update pre-commit hook pre-commit/mirrors-mypy to v1.15.0 ([#3447](https://github.com/nf-core/tools/pull/3447))
- Update prettier to 3.5.0 ([#3448](https://github.com/nf-core/tools/pull/3448))
- chore(deps): update gitpod/workspace-base docker digest to 3aa18f4 ([#3586](https://github.com/nf-core/tools/pull/3586))
- chore(deps): update github actions ([#3488](https://github.com/nf-core/tools/pull/3488))
- chore(deps): update github actions ([#3498](https://github.com/nf-core/tools/pull/3498))
- chore(deps): update dependency textual to v2 ([#3471](https://github.com/nf-core/tools/pull/3471))
- chore(deps): update actions/setup-python digest to 8d9ed9a ([#3518](https://github.com/nf-core/tools/pull/3518))
- chore(deps): update actions/github-script action to v7 ([#3545](https://github.com/nf-core/tools/pull/3545))
- chore(deps): pin dependencies ([#3554](https://github.com/nf-core/tools/pull/3554))
- chore(deps): update codecov/codecov-action digest to 18283e0 ([#3575](https://github.com/nf-core/tools/pull/3575))

## [v3.2.1 - Pewter Pangolin Patch](https://github.com/nf-core/tools/releases/tag/3.2.1) - [2025-04-29]

### Template

- Run awsfulltest after release, and with dev revision on PRs to master/main ([#3485](https://github.com/nf-core/tools/pull/3485))
- Downgrade nf-schema to fix CI tests ([#3544](https://github.com/nf-core/tools/pull/3544))
- Fail nextflow run test gracefully for `latest everything` ([#3543](https://github.com/nf-core/tools/pull/3543))

## [v3.2.0 - Pewter Pangolin](https://github.com/nf-core/tools/releases/tag/3.2.0) - [2025-01-27]

### Template

- Remove automated release tweets ([#3419](https://github.com/nf-core/tools/pull/3419))
- Update template components ([#3426](https://github.com/nf-core/tools/pull/3426))
- Fix `process.shell` in `nextflow.config` ([#3416](https://github.com/nf-core/tools/pull/3416)) and split into new lines ([#3425](https://github.com/nf-core/tools/pull/3425))

### Modules

- Modules created in pipelines "local" dir now use the full template ([#3256](https://github.com/nf-core/tools/pull/3256))

### Subworkflows

- Subworkflows created in pipelines "local" dir now use the full template ([#3256](https://github.com/nf-core/tools/pull/3256))

### General

- Update pre-commit hook editorconfig-checker/editorconfig-checker.python to v3.1.2 ([#3414](https://github.com/nf-core/tools/pull/3414))
- Update python:3.12-slim Docker digest to 123be56 ([#3421](https://github.com/nf-core/tools/pull/3421))

## [v3.1.2 - Brass Boxfish Patch](https://github.com/nf-core/tools/releases/tag/3.1.2) - [2025-01-20]

### Template

- Bump nf-schema to `2.3.0` ([#3401](https://github.com/nf-core/tools/pull/3401))
- Remove jinja formatting which was deleting line breaks ([#3405](https://github.com/nf-core/tools/pull/3405))

### Download

- Allow `nf-core pipelines download -r` to download commits ([#3374](https://github.com/nf-core/tools/pull/3374))
- Fix faulty Download Test Action to ensure that setup and test run as one job and on the same runner ([#3389](https://github.com/nf-core/tools/pull/3389))

### Modules

- Fix bump-versions: only append module name if it is a dir and contains `main.nf` ([#3384](https://github.com/nf-core/tools/pull/3384))

### General

- `manifest.author` is not required anymore ([#3397](https://github.com/nf-core/tools/pull/3397))
- Parameters schema validation: allow `oneOf`, `anyOf` and `allOf` with `required` ([#3386](https://github.com/nf-core/tools/pull/3386))
- Run pre-comit when rendering template for pipelines sync ([#3371](https://github.com/nf-core/tools/pull/3371))
- Fix sync GHA by removing quotes from parsed branch name ([#3394](https://github.com/nf-core/tools/pull/3394))

## [v3.1.1 - Brass Boxfish Patch](https://github.com/nf-core/tools/releases/tag/3.1.1) - [2024-12-20]

### Template

- Use outputs instead of the environment to pass around values between steps in the Download Test Action ([#3351](https://github.com/nf-core/tools/pull/3351))
- Fix pre commit template ([#3358](https://github.com/nf-core/tools/pull/3358))
- Set LICENSE copyright to nf-core community ([#3366](https://github.com/nf-core/tools/pull/3366))
- Fix including modules.config ([#3356](https://github.com/nf-core/tools/pull/3356))

### Linting

- Linting of pipeline LICENSE file is a warning to allow for author/maintainer names ([#3366](https://github.com/nf-core/tools/pull/3366))

### General

- Add missing p ([#3357](https://github.com/nf-core/tools/pull/3357))
- Use `manifest.contributors` names if available, otherwise default to `manifest.author` ([#3362](https://github.com/nf-core/tools/pull/3362))
- Properly parse the names form `manifest.contributors` ([#3364](https://github.com/nf-core/tools/pull/3364))

## [v3.1.0 - Brass Boxfish](https://github.com/nf-core/tools/releases/tag/3.1.0) - [2024-12-09]

**Highlights**

- We added the new `contributors` field to the pipeline template `manifest`.
- The `nf-core pipelines download` command supports ORAS container URIs.
- New command `nf-core subworkflows patch`.

### Template

- Keep pipeline name in version.yml file ([#3223](https://github.com/nf-core/tools/pull/3223))
- Fix Manifest DOI text ([#3224](https://github.com/nf-core/tools/pull/3224))
- Do not assume pipeline name is url ([#3225](https://github.com/nf-core/tools/pull/3225))
- fix `workflow_dispatch` trigger and parse more review comments in awsfulltest ([#3235](https://github.com/nf-core/tools/pull/3235))
- Add resource limits to Gitpod profile([#3255](https://github.com/nf-core/tools/pull/3255))
- Fix a typo ([#3268](https://github.com/nf-core/tools/pull/3268))
- Remove `def` from `nextflow.config` and add `trace_report_suffix` param ([#3296](https://github.com/nf-core/tools/pull/3296))
- Move `includeConfig 'conf/modules.config'` next to `includeConfig 'conf/base.config'` to not overwrite tests profiles configurations ([#3301](https://github.com/nf-core/tools/pull/3301))
- Use `params.monochrome_logs` in the template and update nf-core components ([#3310](https://github.com/nf-core/tools/pull/3310))
- Fix some typos and improve writing in `usage.md` and `CONTRIBUTING.md` ([#3302](https://github.com/nf-core/tools/pull/3302))
- Add `manifest.contributors` to `nextflow.config` ([#3311](https://github.com/nf-core/tools/pull/3311))
- Update template components ([#3328](https://github.com/nf-core/tools/pull/3328))
- Template: Remove mention of GRCh37 if igenomes is skipped ([#3330](https://github.com/nf-core/tools/pull/3330))
- Be more verbose in approval check action ([#3338](https://github.com/nf-core/tools/pull/3338))
- Add `gpu` profile ([#3272](https://github.com/nf-core/tools/pull/3272))

### Download

- First steps towards fixing [#3179](https://github.com/nf-core/tools/issues/3179): Modify `prioritize_direct_download()` to retain Seqera Singularity `https://` Container URIs and hardcode Seqera Containers into `gather_registries()` ([#3244](https://github.com/nf-core/tools/pull/3244)).
- Further steps towards fixing [#3179](https://github.com/nf-core/tools/issues/3179): Enable limited support for `oras://` container paths (_only absolute URIs, no flexible registries like with Docker_) and prevent unnecessary image downloads for Seqera Container modules with `reconcile_seqera_container_uris()` ([#3293](https://github.com/nf-core/tools/pull/3293)).
- Update dawidd6/action-download-artifact action to v7 ([#3306](https://github.com/nf-core/tools/pull/3306))

### Linting

- allow mixed `str` and `dict` entries in lint config ([#3228](https://github.com/nf-core/tools/pull/3228))
- fix `meta_yml` linting test failing due to `module.process_name` always being `""` ([#3317](https://github.com/nf-core/tools/pull/3317))
- fix module section regex matching wrong things ([#3321](https://github.com/nf-core/tools/pull/3321))

### Modules

- add a panel around diff previews when updating ([#3246](https://github.com/nf-core/tools/pull/3246))

### Subworkflows

- Add `nf-core subworkflows patch` command ([#2861](https://github.com/nf-core/tools/pull/2861))
- Improve subworkflow nf-test migration warning ([#3298](https://github.com/nf-core/tools/pull/3298))

### General

- Include `.nf-core.yml` in `nf-core pipelines bump-version` ([#3220](https://github.com/nf-core/tools/pull/3220))
- create: add shortcut to toggle all switches ([#3226](https://github.com/nf-core/tools/pull/3226))
- Remove unrelated values when saving `.nf-core` file ([#3227](https://github.com/nf-core/tools/pull/3227))
- use correct `--profile` options for `nf-core subworkflows test` ([#3233](https://github.com/nf-core/tools/pull/3233))
- Update GitHub Actions ([#3237](https://github.com/nf-core/tools/pull/3237))
- add `--dir/-d` option to schema commands ([#3247](https://github.com/nf-core/tools/pull/3247))
- fix headers in api docs ([#3323](https://github.com/nf-core/tools/pull/3323))
- handle new schema structure in `nf-core pipelines create-params-file` ([#3276](https://github.com/nf-core/tools/pull/3276))
- Update Gitpod image to use Miniforge instead of Miniconda([#3274](https://github.com/nf-core/tools/pull/3274))
- Add hint to solve git errors with a synced repo ([#3279](https://github.com/nf-core/tools/pull/3279))
- Run pre-commit when testing linting the template pipeline ([#3280](https://github.com/nf-core/tools/pull/3280))
- Make CLI prompt less nf-core specific ([#3326](https://github.com/nf-core/tools/pull/3326))
- Update gitpod vscode extensions to use nf-core extension pack ([#3327](https://github.com/nf-core/tools/pull/3327))
- Remove toList() channel operation from inside onComplete block ([#3304](https://github.com/nf-core/tools/pull/3304))
- build: Setup VS Code tests ([#3292](https://github.com/nf-core/tools/pull/3292))
- Don't break gitpod.yml with template string ([#3332](https://github.com/nf-core/tools/pull/3332))
- rocrate: remove duplicated entries for name and version ([#3333](https://github.com/nf-core/tools/pull/3333))
- rocrate: Update crate with version bump and handle new contributor field ([#3334](https://github.com/nf-core/tools/pull/3334))
- set default_branch to master for now ([#3335](https://github.com/nf-core/tools/issues/3335))
- Set git defaultBranch to master in sync action ([#3337](https://github.com/nf-core/tools/pull/3337))
- Add verbose mode to sync action ([#3339](https://github.com/nf-core/tools/pull/3339))
- ci: Run checks on renovate branches to avoid creating and merging PRs ([#3018](https://github.com/nf-core/tools/pull/3018))

### Version updates

- chore(deps): update pre-commit hook pre-commit/mirrors-mypy to v1.12.0 ([#3230](https://github.com/nf-core/tools/pull/3230))
- Update codecov/codecov-action action to v5 ([#3283](https://github.com/nf-core/tools/pull/3283))
- Update gitpod/workspace-base Docker digest to 12853f7 ([#3309](https://github.com/nf-core/tools/pull/3309))
- Update pre-commit hook astral-sh/ruff-pre-commit to v0.8.2 ([#3325](https://github.com/nf-core/tools/pull/3325))

## [v3.0.2 - Titanium Tapir Patch](https://github.com/nf-core/tools/releases/tag/3.0.2) - [2024-10-11]

### Template

- Add null/ to .gitignore ([#3191](https://github.com/nf-core/tools/pull/3191))
- Parallelize pipeline GHA tests over docker/conda/singularity ([#3214](https://github.com/nf-core/tools/pull/3214))
- Fix `template_version_comment.yml` github action ([#3212](https://github.com/nf-core/tools/pull/3212))
- Fix pre-commit linting on pipeline template ([#3218](https://github.com/nf-core/tools/pull/3218))

### Linting

- Fix bug when linting schema params and when using `defaultIgnoreParams` ([#3213](https://github.com/nf-core/tools/pull/3213))

### General

- Use updated pipeline commands in docstrings ([#3215](https://github.com/nf-core/tools/pull/3215))
- Disable automatic sync on release, fix handling empty pipeline input ([#3217](https://github.com/nf-core/tools/pull/3217))

## [v3.0.1 - Titanium Tapir Patch](https://github.com/nf-core/tools/releases/tag/3.0.1) - [2024-10-09]

### Template

- Fixed an issue where the linting CI action didn't read the correct file ([#3202](https://github.com/nf-core/tools/pull/3202))
- Fixed condition for `awsfulltest` to run ([#3203](https://github.com/nf-core/tools/pull/3203))
- Fix too many empty lines added by jinja ([#3204](https://github.com/nf-core/tools/pull/3204) and [#3206](https://github.com/nf-core/tools/pull/3206))
- Fix header blocks in local subworkflow including git merge marker-like strings ([#3201](https://github.com/nf-core/tools/pull/3201))
- Update included subworkflows and modules ([#3208](https://github.com/nf-core/tools/pull/3208))

## [v3.0.0 - Titanium Tapir](https://github.com/nf-core/tools/releases/tag/3.0.0) - [2024-10-08]

**Highlights**

- Pipeline commands are renamed from `nf-core <command>` to `nf-core pipelines <command>` to follow the same command structure as modules and subworkflows commands.
- More customisation for pipeline templates. The template has been divided into features which can be skipped, e.g. you can create a new pipeline without any traces of FastQC in it.
- A new Text User Interface app when running `nf-core pipelines create` to help us guide you through the process better (no worries, you can still use the cli if you give all values as parameters)
- We replaced nf-validation with nf-schema in the pipeline template
- CI tests now lint with the nf-core tools version matching the template version of the pipeline, to minimise errors in opened PRs with every new tools release.
- `nf-core licences` command is deprecated.
- Changed default branch to `main`.
- The structure of nf-core/tools pytests has been updated.
- The structure of the API docs has been updated.

### Template

- Change paths to test data ([#2985](https://github.com/nf-core/tools/pull/2985))
- Run awsfulltest on PRs to `master` with two PR approvals ([#3042](https://github.com/nf-core/tools/pull/3042))
- Remove deprecated syntax ([#3046](https://github.com/nf-core/tools/pull/3046))
- Use filename in code block for `params.yml` ([#3055](https://github.com/nf-core/tools/pull/3055))
- Remove release announcement for non nf-core pipelines ([#3072](https://github.com/nf-core/tools/pull/3072))
- handle template features with a yaml file ([#3108](https://github.com/nf-core/tools/pull/3108), [#3112](https://github.com/nf-core/tools/pull/3112))
- add option to exclude code linters for custom pipeline template ([#3084](https://github.com/nf-core/tools/pull/3084))
- add option to exclude citations for custom pipeline template ([#3101](https://github.com/nf-core/tools/pull/3101) and [#3169](https://github.com/nf-core/tools/pull/3169))
- add option to exclude gitpod for custom pipeline template ([#3100](https://github.com/nf-core/tools/pull/3100))
- add option to exclude codespaces from pipeline template ([#3105](https://github.com/nf-core/tools/pull/3105))
- add option to exclude multiqc from pipeline template ([#3103](https://github.com/nf-core/tools/pull/3103))
- add option to exclude changelog from custom pipeline template ([#3104](https://github.com/nf-core/tools/pull/3104))
- add option to exclude license from pipeline template ([#3125](https://github.com/nf-core/tools/pull/3125))
- add option to exclude email from pipeline template ([#3126](https://github.com/nf-core/tools/pull/3126))
- add option to exclude nf-schema from the template ([#3116](https://github.com/nf-core/tools/pull/3116))
- add option to exclude fastqc from pipeline template ([#3129](https://github.com/nf-core/tools/pull/3129))
- add option to exclude documentation from pipeline template ([#3130](https://github.com/nf-core/tools/pull/3130))
- add option to exclude test configs from pipeline template ([#3133](https://github.com/nf-core/tools/pull/3133))
- add option to exclude tower.yml from pipeline template ([#3134](https://github.com/nf-core/tools/pull/3134))
- Use nf-schema instead of nf-validation ([#3116](https://github.com/nf-core/tools/pull/3116))
- test pipeline with conda and singularity on PRs to master ([#3149](https://github.com/nf-core/tools/pull/3149))
- run nf-core lint `--release` on PRs to master ([#3148](https://github.com/nf-core/tools/pull/3148))
- Add tests to ensure all files are part of a template customisation group and all groups are tested ([#3099](https://github.com/nf-core/tools/pull/3099))
- Update the syntax of `utils_nfcore_pipeline_pipeline` local subworkflow ([#3166](https://github.com/nf-core/tools/pull/3166))
- Remove if/else block to include `igenomes.config` ([#3168](https://github.com/nf-core/tools/pull/3168))
- Fixed release announcement hashtags for Mastodon ([#3099](https://github.com/nf-core/tools/pull/3176))
- Remove try/catch blocks from `nextflow.config` ([#3167](https://github.com/nf-core/tools/pull/3167))
- Extend `download_pipeline.yml` to count pre-downloaded container images. ([#3182](https://github.com/nf-core/tools/pull/3182))

### Linting

- Fix linting fail on nfcore_external_java_deps if nf_schema is used ([#2976](https://github.com/nf-core/tools/pull/2976))
- Conda module linting: Include package name in log file ([#3014](https://github.com/nf-core/tools/pull/3014))
- Remove defaults from conda `environment.yml` file. ([#3029](https://github.com/nf-core/tools/pull/3029))
- Restructure pipeline tests and move pipeline linting into subfolder ([#3070](https://github.com/nf-core/tools/pull/3070))
- Fix module linting warning for process_high_memory ([#3086](https://github.com/nf-core/tools/issues/3086))
- Linting will now fail when an unpinned plugin is used ([#3116](https://github.com/nf-core/tools/pull/3116))
- Linting will now check if the schema is correct for the used validation plugin ([#3116])(https://github.com/nf-core/tools/pull/3116)
- Linting will now check the use of the right validation plugin include statements in the workflow scripts ([#3116])(https://github.com/nf-core/tools/pull/3116)
- Full linting for correct use of nf-schema and nf-validation ([#3116](https://github.com/nf-core/tools/pull/3116))
- Handle cases where the directory path contains the name of the component ([#3147](https://github.com/nf-core/tools/pull/3147))
- Don't test conda `environment.yml` `name` attribute (which should no longer be there) ([#3161](https://github.com/nf-core/tools/pull/3161))

### Pipeline create command

- Allow more special characters on the pipeline name for non-nf-core pipelines ([#3008](https://github.com/nf-core/tools/pull/3008))
- Mock git cretentials to generate stable textual snapshots ([#3007](https://github.com/nf-core/tools/pull/3007))
- Display input textbox with equally spaced grid ([#3038](https://github.com/nf-core/tools/pull/3038))
- Allow numbers in custom pipeline name ([#3094](https://github.com/nf-core/tools/pull/3094))

### Components

- The `modules_nfcore` tag in the `main.nf.test` file of modules/subworkflows now displays the organization name in custom modules repositories ([#3005](https://github.com/nf-core/tools/pull/3005))
- Add `--migrate_pytest` option to `nf-core <modules|subworkflows> test` command ([#3085](https://github.com/nf-core/tools/pull/3085))
- Allow spaces at the beginning of include statements ([#3115](https://github.com/nf-core/tools/pull/3115))
- Add option `--fix` to update the `meta.yml` file of subworkflows ([#3077](https://github.com/nf-core/tools/pull/3077))

### Download

- Fully removed already deprecated `-t` / `--tower` flag.
- Refactored the CLI for consistency (short flag is usually second word, e.g. also for `--container-library` etc.):

| Old parameter                     | New parameter                     |
| --------------------------------- | --------------------------------- |
| `-d` / `--download-configuration` | `-c` / `--download-configuration` |
| `-p` / `--parallel-downloads`     | `-d` / `--parallel-downloads`     |
| new parameter                     | `-p` / (`--platform`)             |

### General

- Change default branch to `main` for the nf-core/tools repository
- Update output of generation script for API docs to new structure ([#2988](https://github.com/nf-core/tools/pull/2988))
- Remove `rich-codex.yml` action, images are now generated on the website repo ([#2989](https://github.com/nf-core/tools/pull/2989))
- Add no clobber and put bash options on their own line ([#2991](https://github.com/nf-core/tools/pull/2991))
- move pipeline subcommands for v3.0 ([#2983](https://github.com/nf-core/tools/pull/2983))
- return directory if base_dir is the root directory ([#3003](https://github.com/nf-core/tools/pull/3003))
- Remove nf-core licences command ([#3012](https://github.com/nf-core/tools/pull/3012))
- README - absolute image paths ([#3013](https://github.com/nf-core/tools/pull/3013))
- Add warning deprecation message to top-level commands ([#3036](https://github.com/nf-core/tools/pull/3036))
- move pipeline commands to functions to avoid duplication ([#3039](https://github.com/nf-core/tools/pull/3039))
- update output_dir for api docs to new website structure ([#3051](https://github.com/nf-core/tools/pull/3051))
- Add `--limit-output` argument for modules/subworkflow update ([#3047](https://github.com/nf-core/tools/pull/3047))
- update api docs to new structure ([#3054](https://github.com/nf-core/tools/pull/3054))
- handle new jsonschema error type ([#3061](https://github.com/nf-core/tools/pull/3061))
- Fix number of arguments for pipelines_create within the command_create function ([#3074](https://github.com/nf-core/tools/pull/3074))
- Add bot action to update textual snapshots and write bot documentation ([#3102](https://github.com/nf-core/tools/pull/3102))
- Update gitpod setup ([#3136](https://github.com/nf-core/tools/pull/3136))
- fix syncing a pipeline from current directory ([#3143](https://github.com/nf-core/tools/pull/3143))
- Patch gitpod conda setup to not use defaults channel ([#3159](https://github.com/nf-core/tools/pull/3159))

## Version updates

- Update pre-commit hook astral-sh/ruff-pre-commit to v0.6.0 ([#3122](https://github.com/nf-core/tools/pull/3122))
- Update gitpod/workspace-base Docker digest to 92dd1bc ([#2982](https://github.com/nf-core/tools/pull/2982))
- Update python:3.12-slim Docker digest to 59c7332 ([#3124](https://github.com/nf-core/tools/pull/3124))
- Update pre-commit hook pre-commit/mirrors-mypy to v1.11.1 ([#3091](https://github.com/nf-core/tools/pull/3091))
- Update to pytest v8 and move it to dev dependencies ([#3058](https://github.com/nf-core/tools/pull/3058))
- Update minimal textual version and snapshots ([#2998](https://github.com/nf-core/tools/pull/2998))

## [v2.14.1 - Tantalum Toad - Patch](https://github.com/nf-core/tools/releases/tag/2.14.1) - [2024-05-09]

### Template

- Don't cache pip in `linting.yml` ([#2961](https://github.com/nf-core/tools/pull/2961))
- Lint pipelines with the nf-core template version and post comment if it is outdated ([#2978](https://github.com/nf-core/tools/pull/2978))

### General

- Fix update github action for components in pipeline template ([#2968](https://github.com/nf-core/tools/pull/2968))
- Run sync after release on self hosted runners ([#2970](https://github.com/nf-core/tools/pull/2970))

## [v2.14.0 - Tantalum Toad](https://github.com/nf-core/tools/releases/tag/2.14.0) - [2024-05-08]

### Template

- Remove fasta default from nextflow.config ([#2828](https://github.com/nf-core/tools/pull/2828))
- Update templates to use nf-core/setup-nextflow v2 ([#2818](https://github.com/nf-core/tools/pull/2818))
- Link to troubleshooting docs when pipeline fails ([#2845](https://github.com/nf-core/tools/pull/2845))
- Add fallback to `download_pipeline.yml` in case the pipeline does not support stub runs ([#2846](https://github.com/nf-core/tools/pull/2846))
- Set topic variable correctly in the mastodon announcement ([#2848](https://github.com/nf-core/tools/pull/2848))
- Add a cleanup action to `download_pipeline.yml` to fix failures caused by inadequate storage space on the runner ([#2849](https://github.com/nf-core/tools/pull/2849))
- Update python to 3.12 ([#2805](https://github.com/nf-core/tools/pull/2805))
- Remove `pyproject.toml` from template root
- Shorten lines in pipeline template ([#2908](https://github.com/nf-core/tools/pull/2908))
- Add a new hidden `--pipelines_testdata_base_path` parameter to more easily switch locations of test data in test configs (#2931)[https://github.com/nf-core/tools/pull/2931]
- Permanently activated pipeline-specific institutional configs support for all pipelines without need for manual intervention ([#2936](https://github.com/nf-core/tools/pull/2936))
- Template config: `conda.channels`, not `channels` ([#2950](https://github.com/nf-core/tools/pull/2950))
- Handles multiple DOIs + doi.org resolver from manifest.doi ([#2946](https://github.com/nf-core/tools/pull/2946))
- Update included components ([#2949](https://github.com/nf-core/tools/pull/2949))
- Update .editorconfig ([#2953](https://github.com/nf-core/tools/pull/2953))

### Linting

- Only match assignments of params in `main.nf` and not references like `params.aligner == <something>` ([#2833](https://github.com/nf-core/tools/pull/2833))
- Include test for presence of versions in snapshot ([#2888](https://github.com/nf-core/tools/pull/2888))
- Components: set correct sha before running component lint tests ([#2952](https://github.com/nf-core/tools/pull/2952))
- Less strict logo comparison ([#2956](https://github.com/nf-core/tools/pull/2956))
- Handle request errors more gracefully for actions validation ([#2959](https://github.com/nf-core/tools/pull/2959))

### Download

- Replace `--tower` with `--platform`. The former will remain for backwards compatibility for now but will be removed in a future release. ([#2853](https://github.com/nf-core/tools/pull/2853))
- Better error message when GITHUB_TOKEN exists but is wrong/outdated
- New `--tag` argument to add custom tags during a pipeline download ([#2938](https://github.com/nf-core/tools/pull/2938))

### Components

- Handle more complete list of possible git URL forms (ssh:// and ftp:// prefixes specifically) ([#2945](https://github.com/nf-core/tools/pull/2945))
- Fix path in component update script ([#2823](https://github.com/nf-core/tools/pull/2823))

### General

- Update CI to use nf-core/setup-nextflow v2 ([#2819](https://github.com/nf-core/tools/pull/2819))
- Changelog bot: handle also patch version before dev suffix ([#2820](https://github.com/nf-core/tools/pull/2820))
- Add `force_pr` flag to sync, to force a PR even though there are no changes committed ([#2822](https://github.com/nf-core/tools/pull/2822))
- Update prettier to 3.2.5 ([#2830](https://github.com/nf-core/tools/pull/2830))
- Update GitHub Actions ([#2827](https://github.com/nf-core/tools/pull/2827)), ([#2902](https://github.com/nf-core/tools/pull/2902)), ([#2927](https://github.com/nf-core/tools/pull/2927)), ([#2939](https://github.com/nf-core/tools/pull/2939))
- Switch to setup-nf-test ([#2834](https://github.com/nf-core/tools/pull/2834))
- Add tests for assignment and referencing of params in main.nf ([#2841](https://github.com/nf-core/tools/pull/2841))
- Optimize layers in dockerfile ([#2842](https://github.com/nf-core/tools/pull/2842))
- Update python:3.11-slim Docker digest to a2eb07f ([#2847](https://github.com/nf-core/tools/pull/2847))
- Strip out mention of "Nextflow Tower" and replace with "Seqera Platform" wherever possible
- Fix issue with config resolution that was causing nested configs to behave unexpectedly ([#2862](https://github.com/nf-core/tools/pull/2862))
- Fix schema docs console output truncating ([#2880](https://github.com/nf-core/tools/pull/2880))
- Ensure path object converted to string before stripping quotes ([#2878](https://github.com/nf-core/tools/pull/2878))
- Fix incorrect assertions for called_with on mocks ([#2891](https://github.com/nf-core/tools/pull/2891))
- Make cli-provided module/subworkflow names case insensitive ([#2869](https://github.com/nf-core/tools/pull/2869))
- Get immediate parent path name for schema creation ([#2886](https://github.com/nf-core/tools/pull/2886))
- Remove old references to CUSTOMDUMPSOFTWAREVERSIONS and add linting checks ([#2897](https://github.com/nf-core/tools/pull/2897))
- Update pre-commit hook pre-commit/mirrors-mypy to v1.10.0 ([#2933](https://github.com/nf-core/tools/pull/2933))
- Update codecov/codecov-action digest to 5ecb98a ([#2948](https://github.com/nf-core/tools/pull/2948))
- Update gitpod/workspace-base Docker digest to 124f2b8 ([#2943](https://github.com/nf-core/tools/pull/2943))
- fix(collectfile): sort true for methods_description_mqc.yaml ([#2947](https://github.com/nf-core/tools/pull/2947))
- chore(deps): update pre-commit hook astral-sh/ruff-pre-commit to v0.4.3 ([#2951](https://github.com/nf-core/tools/pull/2951))
- Restructure CHANGELOG.md ([#2954](https://github.com/nf-core/tools/pull/2954))
- fix: ensure path object converted to string before stripping quotes ([#2878](https://github.com/nf-core/tools/pull/2878))
- Test data uses paths instead of config map ([#2877](https://github.com/nf-core/tools/pull/2877))

## [v2.13.1 - Tin Puppy Patch](https://github.com/nf-core/tools/releases/tag/2.13) - [2024-02-29]

### Template

- Remove obsolete editor settings in `devcontainer.json` and `gitpod.yml` ([#2795](https://github.com/nf-core/tools/pull/2795))
- Add nf-test test instructions to contributing and PR template ([#2807](https://github.com/nf-core/tools/pull/2807))
- Fix topic extraction step for hashtags in toots ([#2810](https://github.com/nf-core/tools/pull/2810))
- Update modules and subworkflows in the template ([#2811](https://github.com/nf-core/tools/pull/2811))
- Unpin setup-nextflow and action-tower-launch ([#2806](https://github.com/nf-core/tools/pull/2806))
- Add nf-core-version to `.nf-core.yml` ([#2874](https://github.com/nf-core/tools/pull/2874))

### Download

- Improved offline container image resolution by introducing symlinks, fixes issues [#2751](https://github.com/nf-core/tools/issues/2751), [#2644](https://github.com/nf-core/tools/issues/2644) and [demultiplex#164](https://github.com/nf-core/demultiplex/issues/164): ([#2768](https://github.com/nf-core/tools/pull/2768))

### Linting

### Components

### General

- chore(deps): update codecov/codecov-action digest to 0cfda1d ([#2794](https://github.com/nf-core/tools/pull/2794))
- chore(deps): update gitpod/workspace-base docker digest to c15ee2f ([#2799](https://github.com/nf-core/tools/pull/2799))

## [v2.13 - Tin Puppy](https://github.com/nf-core/tools/releases/tag/2.13) - [2024-02-20]

### Template

- Add empty line in README.md to fix badges. ([#2729](https://github.com/nf-core/tools/pull/2729))
- Replace automatic branch detection in `nf-core download` CI test with hardcoded `dev` and input. ([#2727](https://github.com/nf-core/tools/pull/2727))
- Add Github Action to automatically cleanup ubuntu-latest runners to fix runner running out of diskspace errors([#2755](https://github.com/nf-core/tools/issues/2755))
- Fix GitHub Actions CI and Linting badges links ([#2757](https://github.com/nf-core/tools/pull/2757))
- Add hashtags to release announcement on mastodon ([#2761](https://github.com/nf-core/tools/pull/2761))
- update fastqc and multiqc in template ([#2776](https://github.com/nf-core/tools/pull/2776))
- template refactoring: remove the `lib` directory and use nf-core subworkflows ([#2736](https://github.com/nf-core/tools/pull/2736))
- use nf-validation to create an input channel from a sample sheet ([#2736](https://github.com/nf-core/tools/pull/2736))

### Linting

- Make creat-lint-wf composable ([#2733](https://github.com/nf-core/tools/pull/2733))
- Add looser comparison when pipeline logos ([#2744](https://github.com/nf-core/tools/pull/2744))
- Handle multiple aliases in module imports correctly during linting ([#2762](https://github.com/nf-core/tools/pull/2762))
- Switch to markdown based API and error docs ([#2758](https://github.com/nf-core/tools/pull/2758))

### Modules

- Handle dirty local module repos by force checkout of commits and branches if needed ([#2734](https://github.com/nf-core/tools/pull/2734))
- Patch: handle file not found when it is an added file to a module ([#2771](https://github.com/nf-core/tools/pull/2771))
- Handle symlinks when migrating pytest ([#2770](https://github.com/nf-core/tools/pull/2770))
- Add `--profile` parameter to nf-test command ([#2767](https://github.com/nf-core/tools/pull/2767))
- Reduce the sha length in the `nf-core modules list local` and add links to the specific commit ([#2870](https://github.com/nf-core/tools/pull/2870))
- Add links the nf-core module page and to open the local file in VSCode for module lint results ([#2870](https://github.com/nf-core/tools/pull/2870))

### General

- fix ignoring changes in partially templated files (e.g. `.gitignore`) ([#2722](https://github.com/nf-core/tools/pull/2722))
- update ruff to 0.2.0 and add it to pre-commit step ([#2725](https://github.com/nf-core/tools/pull/2725))
- Update codecov/codecov-action digest to e0b68c6 ([#2728](https://github.com/nf-core/tools/pull/2728))
- Update pre-commit hook astral-sh/ruff-pre-commit to v0.2.1 ([#2730](https://github.com/nf-core/tools/pull/2730))
- Update python:3.11-slim Docker digest to 2a746e2 ([#2743](https://github.com/nf-core/tools/pull/2743))
- Update actions/setup-python action to v5 ([#2739](https://github.com/nf-core/tools/pull/2739))
- Update gitpod/workspace-base Docker digest to 45e7617 ([#2747](https://github.com/nf-core/tools/pull/2747))
- chore(deps): pin jlumbroso/free-disk-space action to 54081f1 ([#2756](https://github.com/nf-core/tools/pull/2756))
- chore(deps): update actions/github-script action to v7 ([#2766](https://github.com/nf-core/tools/pull/2766))
- chore(deps): update pre-commit hook astral-sh/ruff-pre-commit to v0.2.2 ([#2769](https://github.com/nf-core/tools/pull/2769))
- Update gitpod/workspace-base Docker digest to 728e1fa ([#2780](https://github.com/nf-core/tools/pull/2780))

## [v2.12.1 - Aluminium Wolf - Patch](https://github.com/nf-core/tools/releases/tag/2.12.1) - [2024-02-01]

### Linting

- Handle default values of type number from nextflow schema ([#2703](https://github.com/nf-core/tools/pull/2703))
- fix ignoring files_unchanged ([#2707](https://github.com/nf-core/tools/pull/2707))

### General

- Update pre-commit hook astral-sh/ruff-pre-commit to v0.1.15 ([#2705](https://github.com/nf-core/tools/pull/2705))
- use types for default value comparison ([#2712](https://github.com/nf-core/tools/pull/2712))
- fix changelog titles ([#2708](https://github.com/nf-core/tools/pull/2708))
- Print relative path not absolute path in logo cmd log output ([#2709](https://github.com/nf-core/tools/pull/2709))
- Update codecov/codecov-action action to v4 ([#2713](https://github.com/nf-core/tools/pull/2713))
- Ignore nf-core-bot in renovate PRs ([#2716](https://github.com/nf-core/tools/pull/2716))

## [v2.12 - Aluminium Wolf](https://github.com/nf-core/tools/releases/tag/2.12) - [2024-01-29]

### Template

- Add a Github Action Workflow to the pipeline template that tests a successful download with `nf-core download` ([#2618](https://github.com/nf-core/tools/pull/2618))
- Use `pre-commit` to lint files in GitHub CI ([#2635](https://github.com/nf-core/tools/pull/2635))
- Use pdiff also on gitpod for nf-test ([#2640](https://github.com/nf-core/tools/pull/2640))
- switch to new image syntax in readme ([#2645](https://github.com/nf-core/tools/pull/2645))
- Add conda channel order to nextflow.config ([#2094](https://github.com/nf-core/tools/pull/2094))
- Fix tyop in pipeline nextflow.config ([#2664](https://github.com/nf-core/tools/pull/2664))
- Remove `nfcore_external_java_deps.jar` from lib directory in pipeline template ([#2675](https://github.com/nf-core/tools/pull/2675))
- Add function to check `-profile` is well formatted ([#2678](https://github.com/nf-core/tools/pull/2678))
- Add new pipeline error message pointing to docs when 'requirement exceeds available memory' error message ([#2680](https://github.com/nf-core/tools/pull/2680))
- add 👀👍🏻🎉😕 reactions to fix-linting-bot action ([#2692](https://github.com/nf-core/tools/pull/2692))

### Linting

- Fix linting of a pipeline with patched custom module ([#2669](https://github.com/nf-core/tools/pull/2669))
- linting a pipeline also lints the installed subworkflows ([#2677](https://github.com/nf-core/tools/pull/2677))
- environment.yml name must be lowercase ([#2676](https://github.com/nf-core/tools/pull/2676))
- allow ignoring specific files when template_strings ([#2686](https://github.com/nf-core/tools/pull/2686))
- lint `nextflow.config` default values match the ones specified in `nextflow_schema.json` ([#2684](https://github.com/nf-core/tools/pull/2684))

### Modules

- Fix empty json output for `nf-core list local` ([#2668](https://github.com/nf-core/tools/pull/2668))

### General

- Run CI-pytests for nf-core tools on self-hosted runners ([#2550](https://github.com/nf-core/tools/pull/2550))
- Add Ruff linter and formatter replacing Black, isort and pyupgrade ([#2620](https://github.com/nf-core/tools/pull/2620))
- Set pdiff as nf-test differ in Docker image for Gitpod ([#2642](https://github.com/nf-core/tools/pull/2642))
- Fix Renovate Dockerfile updating issues ([#2648](https://github.com/nf-core/tools/pull/2648) and [#2651](https://github.com/nf-core/tools/pull/2651))
- Add new subcommand `nf-core tui`, which launches a TUI (terminal user interface) to intuitively explore the command line flags, built using [Trogon](https://github.com/Textualize/trogon) ([#2655](https://github.com/nf-core/tools/pull/2655))
- Add new subcommand: `nf-core logo-create` to output an nf-core logo for a pipeline (instead of going through the website) ([#2662](https://github.com/nf-core/tools/pull/2662))
- Handle api redirects from the old site ([#2672](https://github.com/nf-core/tools/pull/2672))
- Remove redundanct v in pipeline version for emails ([#2667](https://github.com/nf-core/tools/pull/2667))
- add function to check `-profile` is well formatted ([#2678](https://github.com/nf-core/tools/pull/2678))
- Update pre-commit hook astral-sh/ruff-pre-commit to v0.1.14 ([#2674](https://github.com/nf-core/tools/pull/2674))
- Update pre-commit hook pre-commit/mirrors-mypy to v1.8.0 ([#2630](https://github.com/nf-core/tools/pull/2630))
- Update mshick/add-pr-comment action to v2 ([#2632](https://github.com/nf-core/tools/pull/2632))
- update python image version in docker file ([#2636](https://github.com/nf-core/tools/pull/2636))
- Update actions/cache action to v4 ([#2666](https://github.com/nf-core/tools/pull/2666))
- Update peter-evans/create-or-update-comment action to v4 ([#2683](https://github.com/nf-core/tools/pull/2683))
- Update peter-evans/create-or-update-comment action to v4 ([#2695](https://github.com/nf-core/tools/pull/2695))

## [v2.11.1 - Magnesium Dragon Patch](https://github.com/nf-core/tools/releases/tag/2.11) - [2023-12-20]

### Template

- Rename `release-announcments.yml` to `release-announcements.yml` ([#2610](https://github.com/nf-core/tools/pull/2610))
- Fix `nextflow.config` `docker.runOptions` ([#2607](https://github.com/nf-core/tools/pull/2607))

### General

- Only dump `modules.json` when it is modified ([#2609](https://github.com/nf-core/tools/pull/2609))

## [v2.11 - Magnesium Dragon](https://github.com/nf-core/tools/releases/tag/2.11) - [2023-12-19]

### Template

- Fix writing files to a remote outdir in the NfcoreTemplate helper functions ([#2465](https://github.com/nf-core/tools/pull/2465))
- Fancier syntax highlighting for example samplesheets in the usage.md template ([#2503](https://github.com/nf-core/tools/pull/2503))
- Use closure for multiqc ext.args ([#2509](https://github.com/nf-core/tools/pull/2509))
- Fix how the modules template references the conda environment file ([#2540](https://github.com/nf-core/tools/pull/2540))
- Unset env variable JAVA_TOOL_OPTIONS in gitpod ([#2569](https://github.com/nf-core/tools/pull/2569))
- Pin the version of nf-validation ([#2579](https://github.com/nf-core/tools/pull/2579))
- Disable process selector warnings by default ([#2161](https://github.com/nf-core/tools/issues/2161))
- Remove `docker.userEmulation` from nextflow.config in pipeline template ([#2580](https://github.com/nf-core/tools/pull/2580))

### Download

- Add `docker://` prefix for absolute container URIs as well ([#2576](https://github.com/nf-core/tools/pull/2576)).
- Bugfix for AttributeError: `ContainerError` object has no attribute `absoluteURI` ([#2543](https://github.com/nf-core/tools/pull/2543)).

### Linting

- Fix incorrectly failing linting if 'modules' was not found in meta.yml ([#2447](https://github.com/nf-core/tools/pull/2447))
- Correctly pass subworkflow linting test if `COMPONENT.out.versions` is used in the script ([#2448](https://github.com/nf-core/tools/pull/2448))
- Add pyupgrade to pre-commit config and dev requirements as mentioned in [#2200](https://github.com/nf-core/tools/issues/2200)
- Check for spaces in modules container URLs ([#2452](https://github.com/nf-core/tools/issues/2452))
- Correctly ignore `timeline.enabled`, `report.enabled`, `trace.enabled`, `dag.enabled` variables when linting a pipeline. ([#2507](https://github.com/nf-core/tools/pull/2507))
- Lint nf-test main.nf.test tags include all used components in chained tests ([#2572](https://github.com/nf-core/tools/pull/2572))
- Don't fail linting if md5sum for empty files are found in a stub test ([#2571](https://github.com/nf-core/tools/pull/2571))
- Check for existence of test profile ([#2478](https://github.com/nf-core/tools/pull/2478))

### Modules

- Added stub test creation to `create_test_yml` ([#2476](https://github.com/nf-core/tools/pull/2476))
- Replace ModulePatch by ComponentPatch ([#2482](https://github.com/nf-core/tools/pull/2482))
- Fixed `nf-core modules lint` to work with new module structure for nf-test ([#2494](https://github.com/nf-core/tools/pull/2494))
- Add option `--migrate-pytest` to create a module with nf-test taking into account an existing module ([#2549](https://github.com/nf-core/tools/pull/2549))
- When installing modules and subworkflows, automatically create the `./modules` directory if it doesn't exist ([#2563](https://github.com/nf-core/tools/issues/2563))
- When `.nf-core.yml` is not found create it in the current directory instead of the root filesystem ([#2237](https://github.com/nf-core/tools/issues/2237))
- Modules `--migrate-pytest` copies template scripts ([#2568](https://github.com/nf-core/tools/pull/2568))

### Subworkflows

- Added stub test creation to `create_test_yml` ([#2476](https://github.com/nf-core/tools/pull/2476))
- Fixed `nf-core subworkflows lint` to work with new module structure for nf-test ([#2494](https://github.com/nf-core/tools/pull/2494))
- Add option `--migrate-pytest` to create a subworkflow with nf-test taking into account an existing subworkflow ([#2549](https://github.com/nf-core/tools/pull/2549))

### General

- Update `schema build` functionality to automatically update defaults which have changed in the `nextflow.config`([#2479](https://github.com/nf-core/tools/pull/2479))
- Change testing framework for modules and subworkflows from pytest to nf-test ([#2490](https://github.com/nf-core/tools/pull/2490))
- `bump_version` keeps now the indentation level of the updated version entries ([#2514](https://github.com/nf-core/tools/pull/2514))
- Add mypy to pre-commit config for the tools repo ([#2545](https://github.com/nf-core/tools/pull/2545))
- Use Path objects for ComponentCreate and update the structure of components templates ([#2551](https://github.com/nf-core/tools/pull/2551)).
- GitPod base image: swap tool installation back to `conda` from `mamba` ([#2566](https://github.com/nf-core/tools/pull/2566)).
- Sort the `installed_by` list in `modules.json` ([#2570](https://github.com/nf-core/tools/pull/2570)).
- Unset env variable JAVA_TOOL_OPTIONS in gitpod ([#2569](https://github.com/nf-core/tools/pull/2569))

## [v2.10 - Nickel Ostrich](https://github.com/nf-core/tools/releases/tag/2.10) + [2023-09-25]

### Template

- Fix links in `multiqc_config.yml` ([#2372](https://github.com/nf-core/tools/pull/2372) and [#2412](https://github.com/nf-core/tools/pull/2412))
- Remove default false from nextflow_schema.json ([#2376](https://github.com/nf-core/tools/pull/2376))
- Add module MULTIQC to modules.config ([#2377](https://github.com/nf-core/tools/pull/2377))
- Add GitHub workflow for automated release announcements ([#2382](https://github.com/nf-core/tools/pull/2382))
- Update the Code of Conduct ([#2381](https://github.com/nf-core/tools/pull/2381))
- Save template information to `.nf-core.yml` and deprecate argument `--template-yaml` for `nf-core sync` ([#2388](https://github.com/nf-core/tools/pull/2388) and [#2389](https://github.com/nf-core/tools/pull/2389))
- ([#2397](https://github.com/nf-core/tools/pull/2397)) Remove fixed Ubuntu test and added to standard testing matrix
- ([#2396](https://github.com/nf-core/tools/pull/2396)) Reduce container finding error to warning since the registries are not consistent.
- ([#2415](https://github.com/nf-core/tools/pull/2415#issuecomment-1709847086)) Add autoMounts for apptainer.
- Remove `igenomes_base` from the schema, so that nf-validation doesn't create a file path and throw errors offline for s3 objects.
- Modified devcontainer permissions so that singularity can be run in Codespaces/VS Code devcontainers ([Commit a103f44](https://github.com/CarsonJM/tools/commit/a103f4484eca8c6d668e4653a4ed8d20faf1b41d))
- Update Gitpod profile resources to reflect base environment settings.
- ([#747](https://github.com/nf-core/tools/issues/747)) Add to the template the code to dump the selected pipeline parameters into a json file.

### Download

- Improved container image resolution and prioritization of http downloads over Docker URIs ([#2364](https://github.com/nf-core/tools/pull/2364)).
- Registries provided with `-l`/`--container-library` will be ignored for modules with explicit container registry specifications ([#2403](https://github.com/nf-core/tools/pull/2403)).
- Fix unintentional downloading of containers in test for the Tower download functionality. Bug reported by @adamrtalbot and @awgymer ([#2434](https://github.com/nf-core/tools/pull/2434)).

### Linting

- Add new command `nf-core subworkflows lint` ([#2379](https://github.com/nf-core/tools/pull/2379))

### Modules

### Subworkflows

- Fix bug: missing subworkflow name when using `nf-core subworkflows create` ([#2435](https://github.com/nf-core/tools/pull/2435))

### General

- Initialise `docker_image_name` to fix `UnboundLocalError` error ([#2374](https://github.com/nf-core/tools/pull/2374))
- Fix prompt pipeline revision during launch ([#2375](https://github.com/nf-core/tools/pull/2375))
- Add a `create-params-file` command to create a YAML parameter file for a pipeline containing parameter documentation and defaults. ([#2362](https://github.com/nf-core/tools/pull/2362))
- Update the Code of Conduct ([#2381](https://github.com/nf-core/tools/pull/2381))
- Remove `--no-git` option from `nf-core create` ([#2394](https://github.com/nf-core/tools/pull/2394))
- Throw warning when custom workflow name contains special characters ([#2401](https://github.com/nf-core/tools/pull/2401))
- Bump version of nf-test snapshot files with `nf-core bump-version` ([#2410](https://github.com/nf-core/tools/pull/2410))

## [v2.9 - Chromium Falcon](https://github.com/nf-core/tools/releases/tag/2.9) + [2023-06-29]

### Template

- `params.max_multiqc_email_size` is no longer required ([#2273](https://github.com/nf-core/tools/pull/2273))
- Remove `cleanup = true` from `test_full.config` in pipeline template ([#2279](https://github.com/nf-core/tools/pull/2279))
- Fix usage docs for specifying `params.yaml` ([#2279](https://github.com/nf-core/tools/pull/2279))
- Added stub in modules template ([#2277](https://github.com/nf-core/tools/pull/2277)) [Contributed by @nvnieuwk]
- Move registry definitions out of profile scope ([#2286])(https://github.com/nf-core/tools/pull/2286)
- Remove `aws_tower` profile ([#2287])(https://github.com/nf-core/tools/pull/2287)
- Fixed the Slack report to include the pipeline name ([#2291](https://github.com/nf-core/tools/pull/2291))
- Fix link in the MultiQC report to point to exact version of output docs ([#2298](https://github.com/nf-core/tools/pull/2298))
- Updates seqeralabs/action-tower-launch to v2.0.0 ([#2301](https://github.com/nf-core/tools/pull/2301))
- Remove schema validation from `lib` folder and use Nextflow [nf-validation plugin](https://nextflow-io.github.io/nf-validation/) instead ([#1771](https://github.com/nf-core/tools/pull/1771/))
- Fix parsing of container directive when it is not typical nf-core format ([#2306](https://github.com/nf-core/tools/pull/2306))
- Add ability to specify custom registry for linting modules, defaults to quay.io ([#2313](https://github.com/nf-core/tools/pull/2313))
- Add `singularity.registry = 'quay.io'` in pipeline template ([#2305](https://github.com/nf-core/tools/pull/2305))
- Add `apptainer.registry = 'quay.io'` in pipeline template ([#2352](https://github.com/nf-core/tools/pull/2352))
- Bump minimum required NF version in pipeline template from `22.10.1` -> `23.04.0` ([#2305](https://github.com/nf-core/tools/pull/2305))
- Add ability to interpret `docker.registry` from `nextflow.config` file. If not found defaults to quay.io. ([#2318](https://github.com/nf-core/tools/pull/2318))
- Add functions to dynamically include pipeline tool citations in MultiQC methods description section for better reporting. ([#2326](https://github.com/nf-core/tools/pull/2326))
- Remove `--tracedir` parameter ([#2290](https://github.com/nf-core/tools/pull/2290))
- Incorrect config parameter warnings when customising pipeline template ([#2333](https://github.com/nf-core/tools/pull/2333))
- Use markdown syntax in the description for the meta map channels ([#2358](https://github.com/nf-core/tools/pull/2358))

### Download

- Introduce a `--tower` flag for `nf-core download` to obtain pipelines in an offline format suited for [seqeralabs® Nextflow Tower](https://cloud.tower.nf/) ([#2247](https://github.com/nf-core/tools/pull/2247)).
- Refactored the CLI for `--singularity-cache` in `nf-core download` from a flag to an argument. The prior options were renamed to `amend` (container images are only saved in the `$NXF_SINGULARITY_CACHEDIR`) and `copy` (a copy of the image is saved with the download). `remote` was newly introduced and allows to provide a table of contents of a remote cache via an additional argument `--singularity-cache-index` ([#2247](https://github.com/nf-core/tools/pull/2247)).
- Refactored the CLI parameters related to container images. Although downloading other images than those of the Singularity/Apptainer container system is not supported for the time being, a generic name for the parameters seemed preferable. So the new parameter `--singularity-cache-index` introduced in [#2247](https://github.com/nf-core/tools/pull/2247) has been renamed to `--container-cache-index` prior to release ([#2336](https://github.com/nf-core/tools/pull/2336)).
- To address issue [#2311](https://github.com/nf-core/tools/issues/2311), a new parameter `--container-library` was created allowing to specify the container library (registry) from which container images in OCI format (Docker) should be pulled ([#2336](https://github.com/nf-core/tools/pull/2336)).
- Container detection in configs was improved. This allows for DSL2-like container definitions inside the container parameter value provided to process scopes [#2346](https://github.com/nf-core/tools/pull/2346).
- Add apptainer to the list of false positive container strings ([#2353](https://github.com/nf-core/tools/pull/2353)).

#### Updated CLI parameters

| Old parameter         | New parameter                                  |
| --------------------- | ---------------------------------------------- |
| new parameter         | `-d` / `--download-configuration`              |
| new parameter         | `-t` / `--tower`                               |
| `-c`/ `--container`   | `-s` / `--container-system <VALUE>`            |
| new parameter         | `-l` / `--container-library <VALUE>`           |
| `--singularity-cache` | `-u` / `--container-cache-utilisation <VALUE>` |
| new parameter         | `-i` / `--container-cache-index <VALUE>`       |

_In addition, `-r` / `--revision` has been changed to a parameter that can be provided multiple times so several revisions can be downloaded at once._

### Linting

- Warn if container access is denied ([#2270](https://github.com/nf-core/tools/pull/2270))
- Error if module container specification has quay.io as prefix when it shouldn't have ([#2278](https://github.com/nf-core/tools/pull/2278/files)
- Detect if container is 'simple name' and try to contact quay.io server by default ([#2281](https://github.com/nf-core/tools/pull/2281))
- Warn about null/None/empty default values in `nextflow_schema.json` ([#3328](https://github.com/nf-core/tools/pull/2328))
- Fix linting when creating a pipeline skipping some parts of the template and add CI test ([#2330](https://github.com/nf-core/tools/pull/2330))

### Modules

- Don't update `modules_json` object if a module is not updated ([#2323](https://github.com/nf-core/tools/pull/2323))

### Subworkflows

### General

- GitPod base image: Always self-update to the latest version of Nextflow. Add [pre-commit](https://pre-commit.com/) dependency.
- GitPod configs: Update Nextflow as an init task, init pre-commit in pipeline config.
- Refgenie: Create `nxf_home/nf-core/refgenie_genomes.config` path if it doesn't exist ([#2312](https://github.com/nf-core/tools/pull/2312))
- Add CI tests to test running a pipeline when it's created from a template skipping different areas

## [v2.8 - Ruthenium Monkey](https://github.com/nf-core/tools/releases/tag/2.8) - [2023-04-27]

### Template

- Explicitly disable `conda` when a container profile ([#2140](https://github.com/nf-core/tools/pull/2140))
- Turn on automatic clean up of intermediate files in `work/` on successful pipeline completion in full-test config ([#2163](https://github.com/nf-core/tools/pull/2163)) [Contributed by @jfy133]
- Add documentation to `usage.md` on how to use `params.yml` files, based on nf-core/ampliseq text ([#2173](https://github.com/nf-core/tools/pull/2173/)) [Contributed by @jfy133, @d4straub]
- Make jobs automatically resubmit for a much wider range of exit codes (now `104` and `130..145`) ([#2170](https://github.com/nf-core/tools/pull/2170))
- Add a clean-up GHA which closes issues and PRs with specific labels ([#2183](https://github.com/nf-core/tools/pull/2183))
- Remove problematic sniffer code in samplesheet_check.py that could give false positive 'missing header' errors ([https://github.com/nf-core/tools/pull/2194]) [Contributed by @Midnighter, @jfy133]
- Consistent syntax for branch checks in PRs ([#2202](https://github.com/nf-core/tools/issues/2202))
- Fixed minor Jinja2 templating bug that caused the PR template to miss a newline
- Updated AWS tests to use newly moved `seqeralabs/action-tower-launch` instead of `nf-core/tower-action`
- Remove `.cff` files from `.editorconfig` ([#2145](https://github.com/nf-core/tools/pull/2145))
- Simplify pipeline README ([#2186](https://github.com/nf-core/tools/issues/2186))
- Added support for the apptainer container engine via `-profile apptainer`. ([#2244](https://github.com/nf-core/tools/issues/2244)) [Contributed by @jfy133]
- Added config `docker.registry` to pipeline template for a configurable default container registry when using Docker containers. Defaults to `quay.io` ([#2133](https://github.com/nf-core/tools/pull/2133))
- Add tower.yml file to the pipeline template ([#2251](https://github.com/nf-core/tools/pull/2251))
- Add mastodon badge to README ([#2253](https://github.com/nf-core/tools/pull/2253))
- Removed `quay.io` from all module Docker container references as this is now supplied at pipeline level. ([#2249](https://github.com/nf-core/tools/pull/2249))
- Remove `CITATION.cff` file from pipeline template, to avoid that pipeline Zenodo entries reference the nf-core publication instead of the pipeline ([#2059](https://github.com/nf-core/tools/pull/2059)).

### Linting

- Update modules lint test to fail if enable_conda is found ([#2213](https://github.com/nf-core/tools/pull/2213))
- Read module lint configuration from `.nf-core.yml`, not `.nf-core-lint.yml` ([#2221](https://github.com/nf-core/tools/pull/2221))
- `nf-core schema lint` now defaults to linting `nextflow_schema.json` if no filename is provided ([#2225](https://github.com/nf-core/tools/pull/2225))
- Warn if `/zenodo.XXXXXX` is present in the Readme ([#2254](https://github.com/nf-core/tools/pull/2254))
- Lint all labels in a module ([#2227](https://github.com/nf-core/tools/pull/2227))

### Modules

- Add an `--empty-template` option to create a module without TODO statements or examples ([#2175](https://github.com/nf-core/tools/pull/2175) & [#2177](https://github.com/nf-core/tools/pull/2177))
- Removed the `nf-core modules mulled` command and all its code dependencies ([2199](https://github.com/nf-core/tools/pull/2199)).
- Take into account the provided `--git_remote` URL when linting all modules ([2243](https://github.com/nf-core/tools/pull/2243)).

### Subworkflows

- Fixing problem when a module included in a subworkflow had a name change from TOOL to TOOL/SUBTOOL ([#2177](https://github.com/nf-core/tools/pull/2177))
- Fix `nf-core subworkflows test` not running subworkflow tests ([#2181](https://github.com/nf-core/tools/pull/2181))
- Add tests for `nf-core subworkflows create-test-yml` ([#2219](https://github.com/nf-core/tools/pull/2219))

### General

- Deprecate Python 3.7 support because it reaches EOL ([#2210](https://github.com/nf-core/tools/pull/2210))
- `nf-core modules/subworkflows info` now prints the include statement for the module/subworkflow ([#2182](https://github.com/nf-core/tools/pull/2182)).
- Add a clean-up GHA which closes issues and PRs with specific labels ([#2183](https://github.com/nf-core/tools/pull/2183))
- update minimum version of rich to 13.3.1 ([#2185](https://github.com/nf-core/tools/pull/2185))
- Add the Nextflow version to Gitpod container matching the minimal Nextflow version for nf-core (according to `nextflow.config`) ([#2196](https://github.com/nf-core/tools/pull/2196))
- Use `nfcore/gitpod:dev` container in the dev branch ([#2196](https://github.com/nf-core/tools/pull/2196))
- Replace requests_mock with responses in test mocks ([#2165](https://github.com/nf-core/tools/pull/2165)).
- Add warning when installing a module from an `org_path` that exists in multiple remotes in `modules.json` ([#2228](https://github.com/nf-core/tools/pull/2228) [#2239](https://github.com/nf-core/tools/pull/2239)).
- Add the possibility to translate refgenie asset aliases to the ones used in a pipeline with an alias_translations.yaml file ([#2242](https://github.com/nf-core/tools/pull/2242)).
- Add initial CHM13 support ([1988](https://github.com/nf-core/tools/issues/1988))

## [v2.7.2 - Mercury Eagle Patch](https://github.com/nf-core/tools/releases/tag/2.7.2) - [2022-12-19]

### Template

- Fix the syntax of github_output in GitHub actions ([#2114](https://github.com/nf-core/tools/pull/2114))
- Fix a bug introduced in 2.7 that made pipelines hang ([#2132](https://github.com/nf-core/tools/issues/2132))

### Linting

- Allow specifying containers in less than three lines ([#2121](https://github.com/nf-core/tools/pull/2121))
- Run prettier after dumping a json schema file ([#2124](https://github.com/nf-core/tools/pull/2124))

### General

- Only check that a pipeline name doesn't contain dashes if the name is provided by prompt of `--name`. Don't check if a template file is used. ([#2123](https://github.com/nf-core/tools/pull/2123))
- Deprecate `--enable_conda` parameter. Use `conda.enable` instead ([#2131](https://github.com/nf-core/tools/pull/2131))
- Handle `json.load()` exceptions ([#2134](https://github.com/nf-core/tools/pull/2134))

## [v2.7.1 - Mercury Eagle Patch](https://github.com/nf-core/tools/releases/tag/2.7.1) - [2022-12-08]

- Patch release to fix pipeline sync ([#2110](https://github.com/nf-core/tools/pull/2110))

## [v2.7 - Mercury Eagle](https://github.com/nf-core/tools/releases/tag/2.7) - [2022-12-07]

Another big release with lots of new features and bug fixes. Thanks to all contributors!

**Highlights**

- New `nf-core subworkflows` subcommand for creating, removing, testing, updating and finding subworkflows, see the [documentation](https://nf-co.re/tools/#subworkflows) for more information.
- Every pipeline has now it's own GitHub codespace template, which can be used to develop the pipeline directly in the browser.
- Improved handling of modules and subworkflows from other repos than nf-core/modules.
- Pre-commit is now installed as a dependency, which allows us, besides other things, to run prettier on the fly even if it is not manually installed.
- Shell completion for nf-core commands, more information [here](https://nf-co.re/tools#shell-completion).

### Template

#### Features

- Ignore files in `bin/` directory when running prettier ([#2080](https://github.com/nf-core/tools/pull/1957)).
- Add GitHub codespaces template ([#1957](https://github.com/nf-core/tools/pull/1957))
- `nextflow run <pipeline> --version` will now print the workflow version from the manifest and exit ([#1951](https://github.com/nf-core/tools/pull/1951)).
- Add profile for running `docker` with the ARM chips (including Apple silicon) ([#1942](https://github.com/nf-core/tools/pull/1942) and [#2034](https://github.com/nf-core/tools/pull/2034)).
- Flip execution order of parameter summary printing and parameter validation to prevent 'hiding' of parameter errors ([#2033](https://github.com/nf-core/tools/pull/2033)).
- Change colour of 'pipeline completed successfully, but some processes failed' from red to yellow ([#2096](https://github.com/nf-core/tools/pull/2096)).

#### Bug fixes

- Fix lint warnings for `samplesheet_check.nf` module ([#1875](https://github.com/nf-core/tools/pull/1875)).
- Check that the workflow name provided with a template doesn't contain dashes ([#1822](https://github.com/nf-core/tools/pull/1822))

### Linting

#### Features

- Add `--sort-by` option to linting which allows ordering module lint warnings/errors by either test name or module name ([#2077](https://github.com/nf-core/tools/pull/2077)).

#### Bug fixes

- Don't lint pipeline name if `manifest.name` in `.nf-core.yml` ([#2035](https://github.com/nf-core/tools/pull/2035))
- Don't check for `docker pull` commands in `actions_ci` lint test (leftover from DSL1) ([#2055](https://github.com/nf-core/tools/pull/2055)).

### General

#### Features

- Use pre-commit run prettier if prettier is not available ([#1983](https://github.com/nf-core/tools/pull/1983)) and initialize pre-commit in gitpod and codespaces ([#1957](https://github.com/nf-core/tools/pull/1957)).
- Refactor CLI flag `--hide-progress` to be at the top-level group, like `--verbose` ([#2016](https://github.com/nf-core/tools/pull/2016))
- `nf-core sync` now supports the template YAML file using `-t/--template-yaml` ([#1880](https://github.com/nf-core/tools/pull/1880)).
- The default branch can now be specified when creating a new pipeline repo [#1959](https://github.com/nf-core/tools/pull/1959).
- Only warn when checking that the pipeline directory contains a `main.nf` and a `nextflow.config` file if the pipeline is not an nf-core pipeline [#1964](https://github.com/nf-core/tools/pull/1964)
- Bump promoted Python version from 3.7 to 3.8 ([#1971](https://github.com/nf-core/tools/pull/1971)).
- Extended the chat notifications to Slack ([#1829](https://github.com/nf-core/tools/pull/1829)).
- Don't print source file + line number on logging messages (except when verbose) ([#2015](https://github.com/nf-core/tools/pull/2015))
- Automatically format `test.yml` content with Prettier ([#2078](https://github.com/nf-core/tools/pull/2078))
- Automatically format `modules.json` content with Prettier ([#2074](https://github.com/nf-core/tools/pull/2074))
- Add shell completion for nf-core tools commands([#2070](https://github.com/nf-core/tools/pull/2070))

#### Bug fixes, maintenance and tests

- Fix error in tagging GitPod docker images during releases ([#1874](https://github.com/nf-core/tools/pull/1874)).
- Fix bug when updating modules from old version in old folder structure ([#1908](https://github.com/nf-core/tools/pull/1908)).
- Don't remove local copy of modules repo, only update it with fetch ([#1881](https://github.com/nf-core/tools/pull/1881)).
- Improve test coverage of `sync.py` and `__main__.py` ([#1936](https://github.com/nf-core/tools/pull/1936), [#1965](https://github.com/nf-core/tools/pull/1965)).
- Add file `versions.yml` when generating `test.yml` with `nf-core modules create-test-yml` but don't check for md5sum [#1963](https://github.com/nf-core/tools/pull/1963).
- Mock biocontainers and anaconda api calls in modules and subworkflows tests [#1967](https://github.com/nf-core/tools/pull/1967)
- Run tests with Python 3.11 ([#1970](https://github.com/nf-core/tools/pull/1970)).
- Run test with a realistic version of git ([#2043](https://github.com/nf-core/tools/pull/2043)).
- Fix incorrect file deletion in `nf-core launch` when `--params_in` has the same name as `--params_out` ([#1986](https://github.com/nf-core/tools/pull/1986)).
- Updated GitHub actions ([#1998](https://github.com/nf-core/tools/pull/1998), [#2001](https://github.com/nf-core/tools/pull/2001))
- Code maintenance ([#1818](https://github.com/nf-core/tools/pull/1818), [#2032](https://github.com/nf-core/tools/pull/2032), [#2073](https://github.com/nf-core/tools/pull/2073)).
- Track from where modules and subworkflows are installed ([#1999](https://github.com/nf-core/tools/pull/1999)).
- Substitute ModulesCommand and SubworkflowsCommand by ComponentsCommand ([#2000](https://github.com/nf-core/tools/pull/2000)).
- Prevent installation with unsupported Python versions ([#2075](https://github.com/nf-core/tools/pull/2075)).
- Allow other remote URLs not starting with `http` ([#2061](https://github.com/nf-core/tools/pull/2061))

### Modules

- Update patch file paths if the modules directory has the old structure ([#1878](https://github.com/nf-core/tools/pull/1878)).
- Don't write to `modules.json` file when applying a patch file during `nf-core modules update` ([#2017](https://github.com/nf-core/tools/pull/2017)).

### Subworkflows

- Add subworkflow commands `create-test-yml`, `create` and `install` ([#1897](https://github.com/nf-core/tools/pull/1897)).
- Update subworkflows install so it installs also imported modules and subworkflows ([#1904](https://github.com/nf-core/tools/pull/1904)).
- `check_up_to_date()` function from `modules_json.py` also checks for subworkflows ([#1934](https://github.com/nf-core/tools/pull/1934)).
- Add tests for `nf-core subworkflows install` command ([#1996](https://github.com/nf-core/tools/pull/1996)).
- Function `create()` from `modules_json.py` adds also subworkflows to `modules.json` file ([#2005](https://github.com/nf-core/tools/pull/2005)).
- Add `nf-core subworkflows update` command ([#2019](https://github.com/nf-core/tools/pull/2019)).

## [v2.6 - Tin Octopus](https://github.com/nf-core/tools/releases/tag/2.6) - [2022-10-04]

### Template

- Add template for subworkflows
- Add `actions/upload-artifact` step to the awstest workflows, to expose the debug log file
- Add `prettier` as a requirement to Gitpod Dockerimage
- Bioconda incompatible conda channel setups now result in more informative error messages ([#1812](https://github.com/nf-core/tools/pull/1812))
- Improve template customisation documentation ([#1821](https://github.com/nf-core/tools/pull/1821))
- Update MultiQC module, update supplying MultiQC default and custom config and logo files to module
- Add a 'recommend' methods description text to MultiQC to help pipeline users report pipeline usage in publications ([#1749](https://github.com/nf-core/tools/pull/1749))
- Fix template spacing modified by JINJA ([#1830](https://github.com/nf-core/tools/pull/1830))
- Fix MultiQC execution on template ([#1855](https://github.com/nf-core/tools/pull/1855))
- Don't skip including `base.config` when skipping nf-core/configs

### Linting

- Pipelines: Check that the old renamed `lib` files are not still present:
  - `Checks.groovy` -> `Utils.groovy`
  - `Completion.groovy` -> `NfcoreTemplate.groovy`
  - `Workflow.groovy` -> `WorkflowMain.groovy`

### General

- Add function to enable chat notifications on MS Teams, accompanied by `hook_url` param to enable it.
- Schema: Remove `allOf` if no definition groups are left.
- Use contextlib to temporarily change working directories ([#1819](https://github.com/nf-core/tools/pull/1819))
- More helpful error messages if `nf-core download` can't parse a singularity image download
- Add `nf-core subworkflows create` command

### Modules

- If something is wrong with the local repo cache, offer to delete it and try again ([#1850](https://github.com/nf-core/tools/issues/1850))
- Restructure code to work with the directory restructuring in [modules](https://github.com/nf-core/modules/pull/2141) ([#1859](https://github.com/nf-core/tools/pull/1859))
- Make `label: process_single` default when creating a new module

## [v2.5.1 - Gold Otter Patch](https://github.com/nf-core/tools/releases/tag/2.5.1) - [2022-08-31]

- Patch release to fix black linting in pipelines ([#1789](https://github.com/nf-core/tools/pull/1789))
- Add isort options to pyproject.toml ([#1792](https://github.com/nf-core/tools/pull/1792))
- Lint pyproject.toml file exists and content ([#1795](https://github.com/nf-core/tools/pull/1795))
- Update GitHub PyPI package release action to v1 ([#1785](https://github.com/nf-core/tools/pull/1785))

### Template

- Update GitHub actions to use nodejs16 ([#1944](https://github.com/nf-core/tools/pull/1944))

## [v2.5 - Gold Otter](https://github.com/nf-core/tools/releases/tag/2.5) - [2022-08-30]

### Template

- Bumped Python version to 3.7 in the GitHub linting in the workflow template ([#1680](https://github.com/nf-core/tools/pull/1680))
- Fix bug in pipeline readme logo URL ([#1590](https://github.com/nf-core/tools/pull/1590))
- Switch CI to use [setup-nextflow](https://github.com/nf-core/setup-nextflow) action to install Nextflow ([#1650](https://github.com/nf-core/tools/pull/1650))
- Add `CITATION.cff` [#361](https://github.com/nf-core/tools/issues/361)
- Add Gitpod and Mamba profiles to the pipeline template ([#1673](https://github.com/nf-core/tools/pull/1673))
- Remove call to `getGenomeAttribute` in `main.nf` when running `nf-core create` without iGenomes ([#1670](https://github.com/nf-core/tools/issues/1670))
- Make `nf-core create` fail if Git default branch name is dev or TEMPLATE ([#1705](https://github.com/nf-core/tools/pull/1705))
- Convert `console` snippets to `bash` snippets in the template where applicable ([#1729](https://github.com/nf-core/tools/pull/1729))
- Add `branch` field to module entries in `modules.json` to record what branch a module was installed from ([#1728](https://github.com/nf-core/tools/issues/1728))
- Add customisation option to remove all GitHub support with `nf-core create` ([#1766](https://github.com/nf-core/tools/pull/1766))

### Linting

- Check that the `.prettierignore` file exists and that starts with the same content.
- Update `readme.py` nf version badge validation regexp to accept any signs before version number ([#1613](https://github.com/nf-core/tools/issues/1613))
- Add isort configuration and GitHub workflow ([#1538](https://github.com/nf-core/tools/pull/1538))
- Use black also to format python files in workflows ([#1563](https://github.com/nf-core/tools/pull/1563))
- Add check for mimetype in the `input` parameter. ([#1647](https://github.com/nf-core/tools/issues/1647))
- Check that the singularity and docker tags are parsable. Add `--fail-warned` flag to `nf-core modules lint` ([#1654](https://github.com/nf-core/tools/issues/1654))
- Handle exception in `nf-core modules lint` when process name doesn't start with process ([#1733](https://github.com/nf-core/tools/issues/1733))

### General

- Remove support for Python 3.6 ([#1680](https://github.com/nf-core/tools/pull/1680))
- Add support for Python 3.9 and 3.10 ([#1680](https://github.com/nf-core/tools/pull/1680))
- Invoking Python with optimizations no longer affects the program control flow ([#1685](https://github.com/nf-core/tools/pull/1685))
- Update `readme` to drop `--key` option from `nf-core modules list` and add the new pattern syntax
- Add `--fail-warned` flag to `nf-core lint` to make warnings fail ([#1593](https://github.com/nf-core/tools/pull/1593))
- Add `--fail-warned` flag to pipeline linting workflow ([#1593](https://github.com/nf-core/tools/pull/1593))
- Updated the nf-core package requirements ([#1620](https://github.com/nf-core/tools/pull/1620), [#1757](https://github.com/nf-core/tools/pull/1757), [#1756](https://github.com/nf-core/tools/pull/1756))
- Remove dependency of the mock package and use unittest.mock instead ([#1696](https://github.com/nf-core/tools/pull/1696))
- Fix and improve broken test for Singularity container download ([#1622](https://github.com/nf-core/tools/pull/1622))
- Use [`$XDG_CACHE_HOME`](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) or `~/.cache` instead of `$XDG_CONFIG_HOME` or `~/config/` as base directory for API cache
- Switch CI to use [setup-nextflow](https://github.com/nf-core/setup-nextflow) action to install Nextflow ([#1650](https://github.com/nf-core/tools/pull/1650))
- Add tests for `nf-core modules update` and `ModulesJson`.
- Add CI for GitLab remote [#1646](https://github.com/nf-core/tools/issues/1646)
- Add `CITATION.cff` [#361](https://github.com/nf-core/tools/issues/361)
- Allow customization of the `nf-core` pipeline template when using `nf-core create` ([#1548](https://github.com/nf-core/tools/issues/1548))
- Add Refgenie integration: updating of nextflow config files with a refgenie database ([#1090](https://github.com/nf-core/tools/pull/1090))
- Fix `--key` option in `nf-core lint` when supplying a module lint test name ([#1681](https://github.com/nf-core/tools/issues/1681))
- Add `no_git=True` when creating a new pipeline and initialising a git repository is not needed in `nf-core lint` and `nf-core bump-version` ([#1709](https://github.com/nf-core/tools/pull/1709))
- Move `strip_ansi_code` function in lint to `utils.py`
- Simplify control flow and don't use equality comparison for `None` and booleans
- Replace use of the deprecated `distutils` Version object with that from `packaging` ([#1735](https://github.com/nf-core/tools/pull/1735))
- Add code to cancel CI run if a new run starts ([#1760](https://github.com/nf-core/tools/pull/1760))
- CI for the API docs generation now uses the ubuntu-latest base image ([#1762](https://github.com/nf-core/tools/pull/1762))
- Add option to hide progress bars in `nf-core lint` and `nf-core modules lint` with `--hide-progress`.

### Modules

- Add `--fix-version` flag to `nf-core modules lint` command to update modules to the latest version ([#1588](https://github.com/nf-core/tools/pull/1588))
- Fix a bug in the regex extracting the version from biocontainers URLs ([#1598](https://github.com/nf-core/tools/pull/1598))
- Update how we interface with git remotes. ([#1626](https://github.com/nf-core/tools/issues/1626))
- Add prompt for module name to `nf-core modules info` ([#1644](https://github.com/nf-core/tools/issues/1644))
- Update docs with example of custom git remote ([#1645](https://github.com/nf-core/tools/issues/1645))
- Command `nf-core modules test` obtains module name suggestions from installed modules ([#1624](https://github.com/nf-core/tools/pull/1624))
- Add `--base-path` flag to `nf-core modules` to specify the base path for the modules in a remote. Also refactored `modules.json` code. ([#1643](https://github.com/nf-core/tools/issues/1643)) Removed after ([#1754](https://github.com/nf-core/tools/pull/1754))
- Rename methods in `ModulesJson` to remove explicit reference to `modules.json`
- Fix inconsistencies in the `--save-diff` flag `nf-core modules update`. Refactor `nf-core modules update` ([#1536](https://github.com/nf-core/tools/pull/1536))
- Fix bug in `ModulesJson.check_up_to_date` causing it to ask for the remote of local modules
- Handle errors when updating module version with `nf-core modules update --fix-version` ([#1671](https://github.com/nf-core/tools/pull/1671))
- Make `nf-core modules update --save-diff` work when files were created or removed ([#1694](https://github.com/nf-core/tools/issues/1694))
- Get the latest common build for Docker and Singularity containers of a module ([#1702](https://github.com/nf-core/tools/pull/1702))
- Add short option for `--no-pull` option in `nf-core modules`
- Add `nf-core modules patch` command ([#1312](https://github.com/nf-core/tools/issues/1312))
- Add support for patch in `nf-core modules update` command ([#1312](https://github.com/nf-core/tools/issues/1312))
- Add support for patch in `nf-core modules lint` command ([#1312](https://github.com/nf-core/tools/issues/1312))
- Add support for custom remotes in `nf-core modules lint` ([#1715](https://github.com/nf-core/tools/issues/1715))
- Make `nf-core modules` commands work with arbitrary git remotes ([#1721](https://github.com/nf-core/tools/issues/1721))
- Add links in `README.md` for `info` and `patch` commands ([#1722](https://github.com/nf-core/tools/issues/1722)])
- Fix misc. issues with `--branch` and `--base-path` ([#1726](https://github.com/nf-core/tools/issues/1726))
- Add `branch` field to module entries in `modules.json` to record what branch a module was installed from ([#1728](https://github.com/nf-core/tools/issues/1728))
- Fix broken link in `nf-core modules info`([#1745](https://github.com/nf-core/tools/pull/1745))
- Fix unbound variable issues and minor refactoring [#1742](https://github.com/nf-core/tools/pull/1742/)
- Recreate modules.json file instead of complaining about incorrectly formatted file. ([#1741](https://github.com/nf-core/tools/pull/1741)
- Add support for patch when creating `modules.json` file ([#1752](https://github.com/nf-core/tools/pull/1752))

## [v2.4.1 - Cobolt Koala Patch](https://github.com/nf-core/tools/releases/tag/2.4) - [2022-05-16]

- Patch release to try to fix the template sync ([#1585](https://github.com/nf-core/tools/pull/1585))
- Avoid persistent temp files from pytests ([#1566](https://github.com/nf-core/tools/pull/1566))
- Add option to trigger sync manually on just nf-core/testpipeline

## [v2.4 - Cobolt Koala](https://github.com/nf-core/tools/releases/tag/2.4) - [2022-05-16]

### Template

- Read entire lines when sniffing the samplesheet format (fix [#1561](https://github.com/nf-core/tools/issues/1561))
- Add actions workflow to respond to `@nf-core-bot fix linting` comments on pipeline PRs
- Fix Prettier formatting bug in completion email HTML template ([#1509](https://github.com/nf-core/tools/issues/1509))
- Fix bug in pipeline readme logo URL
- Set the default DAG graphic output to HTML to have a default that does not depend on Graphviz being installed on the host system ([#1512](https://github.com/nf-core/tools/pull/1512)).
- Removed retry strategy for AWS tests CI, as Nextflow now handles spot instance retries itself
- Add `.prettierignore` file to stop Prettier linting tests from running over test files
- Made module template test command match the default used in `nf-core modules create-test-yml` ([#1562](https://github.com/nf-core/tools/issues/1562))
- Removed black background from Readme badges now that GitHub has a dark mode, added Tower launch badge.
- Don't save md5sum for `versions.yml` when running `nf-core modules create-test-yml` ([#1511](https://github.com/nf-core/tools/pull/1511))

### General

- Add actions workflow to respond to `@nf-core-bot fix linting` comments on nf-core/tools PRs
- Use [`$XDG_CONFIG_HOME`](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) or `~/.config/nf-core` instead of `~/.nfcore` for API cache (the latter can be safely deleted)
- Consolidate GitHub API calls into a shared function that uses authentication from the [`gh` GitHub cli tool](https://cli.github.com/) or `GITHUB_AUTH_TOKEN` to avoid rate limiting ([#1499](https://github.com/nf-core/tools/pull/1499))
- Add an empty line to `modules.json`, `params.json` and `nextflow-schema.json` when dumping them to avoid prettier errors.
- Remove empty JSON schema definition groups to avoid usage errors ([#1419](https://github.com/nf-core/tools/issues/1419))
- Bumped the minimum version of `rich` from `v10` to `v10.7.0`

### Modules

- Add a new command `nf-core modules mulled` which can generate the name for a multi-tool container image.
- Add a new command `nf-core modules test` which runs pytests locally.
- Print include statement to terminal when `modules install` ([#1520](https://github.com/nf-core/tools/pull/1520))
- Allow follow links when generating `test.yml` file with `nf-core modules create-test-yml` ([1570](https://github.com/nf-core/tools/pull/1570))
- Escaped test run output before logging it, to avoid a rich `MarkupError`

### Linting

- Don't allow a `.nf-core.yaml` file, should be `.yml` ([#1515](https://github.com/nf-core/tools/pull/1515)).
- `shell` blocks now recognised to avoid error `when: condition has too many lines` ([#1557](https://github.com/nf-core/tools/issues/1557))
- Fixed error when using comments after `input` tuple lines ([#1542](https://github.com/nf-core/tools/issues/1542))
- Don't lint the `shell` block when `script` is used ([1558](https://github.com/nf-core/tools/pull/1558))
- Check that `template` is used in `script` blocks
- Tweaks to CLI output display of lint results

## [v2.3.2 - Mercury Vulture Fixed Formatting](https://github.com/nf-core/tools/releases/tag/2.3.2) - [2022-03-24]

Very minor patch release to fix the full size AWS tests and re-run the template sync, which partially failed due to GitHub pull-requests being down at the time of release.

### Template

- Updated the AWS GitHub actions to let nf-core/tower-action use it's defaults for pipeline and git sha ([#1488](https://github.com/nf-core/tools/pull/1488))
- Add prettier editor extension to `gitpod.yml` in template ([#1485](https://github.com/nf-core/tools/pull/1485))
- Remove traces of markdownlint in the template ([#1486](https://github.com/nf-core/tools/pull/1486)
- Remove accidentally added line in `CHANGELOG.md` in the template ([#1487](https://github.com/nf-core/tools/pull/1487))
- Update linting to check that `.editorconfig` is there and `.yamllint.yml` isn't.

## [v2.3.1 - Mercury Vulture Formatting](https://github.com/nf-core/tools/releases/tag/2.3.1) - [2022-03-23]

This patch release is primarily to address problems that we had in the v2.3 release with code linting.
Instead of resolving those specific issues, we chose to replace the linting tools (`markdownlint`, `yamllint`) with a new tool: [_Prettier_](https://prettier.io)

This is a fairly major change and affects a lot of files. However, it will hopefully simplify future usage.
Prettier can auto-format many different file formats (for pipelines the most relevant are markdown and YAML) and is extensible with plugins ([Nextflow](https://github.com/nf-core/prettier-plugin-nextflow), anyone?).
It tends to be a bit less strict than `markdownlint` and `yamllint` and importantly _can fix files for you_ rather than just complaining.

The sync PR may be a little big because of many major changes (whitespace, quotation mark styles etc).
To help with the merge, _**we highly recommend running Prettier on your pipeline's codebase before attempting the template merge**_.
If you take this approach, please copy `.editorconfig` and `.prettierrc.yml` from the template to your pipeline root first,
as they configure the behaviour of Prettier.

To run Prettier, go to the base of the repository where `.editorconfig` and `.prettierrc.yml` are located.
Make sure your `git status` is clean so that the changes don't affect anything you're working on and run:

```bash
prettier --write .
```

This runs Prettier and tells it to fix any issues it finds in place.

Please note that there are many excellent integrations for Prettier available, for example VSCode can be set up to automatically format files on save.

### Template

- Replace `markdownlint` and `yamllint` with [_Prettier_](https://prettier.io) for linting formatting / whitespace ([#1470](https://github.com/nf-core/tools/pull/1470))
- Add CI test using `editorconfig-checker` for other file types to look for standardised indentation and formatting ([#1476](https://github.com/nf-core/tools/pull/1476))
- Add md5sum check of `versions.yml` to `test.yml` on the modules template.
- Update bundled module wrappers to latest versions ([#1462](https://github.com/nf-core/tools/pull/1462))
- Renamed `assets/multiqc_config.yaml` to `assets/multiqc_config.yml` (`yml` not `yaml`) ([#1471](https://github.com/nf-core/tools/pull/1471))

### General

- Convert nf-core/tools API / lint test documentation to MyST ([#1245](https://github.com/nf-core/tools/pull/1245))
- Build documentation for the `nf-core modules lint` tests ([#1250](https://github.com/nf-core/tools/pull/1250))
- Fix some colours in the nf-core/tools API docs ([#1467](https://github.com/nf-core/tools/pull/1467))
- Install tools inside GitPod Docker using the repo itself and not from Conda.
- Rewrite GitHub Actions workflow for publishing the GitPod Docker image.
- Improve config for PyTest so that you can run `pytest` instead of `pytest tests/` ([#1461](https://github.com/nf-core/tools/pull/1461))
- New pipeline lint test `multiqc_config` that checks YAML structure instead of basic file contents ([#1461](https://github.com/nf-core/tools/pull/1461))
- Updates to the GitPod docker image to install the latest version of nf-core/tools

## [v2.3 - Mercury Vulture](https://github.com/nf-core/tools/releases/tag/2.3) - [2022-03-15]

### Template

- Removed mention of `--singularity_pull_docker_container` in pipeline `README.md`
- Replaced equals with ~ in nf-core headers, to stop false positive unresolved conflict errors when committing with VSCode.
- Add retry strategy for AWS megatests after releasing [nf-core/tower-action v2.2](https://github.com/nf-core/tower-action/releases/tag/v2.2)
- Added `.nf-core.yml` file with `repository_type: pipeline` for modules commands
- Update igenomes path to the `BWAIndex` to fetch the whole `version0.6.0` folder instead of only the `genome.fa` file
- Remove pinned Node version in the GitHub Actions workflows, to fix errors with `markdownlint`
- Bumped `nf-core/tower-action` to `v3` and removed `pipeline` and `revision` from the AWS workflows, which were not needed
- Add yamllint GitHub Action.
- Add `.yamllint.yml` to avoid line length and document start errors ([#1407](https://github.com/nf-core/tools/issues/1407))
- Add `--publish_dir_mode` back into the pipeline template ([nf-core/rnaseq#752](https://github.com/nf-core/rnaseq/issues/752#issuecomment-1039451607))
- Add optional loading of of pipeline-specific institutional configs to `nextflow.config`
- Make `--outdir` a mandatory parameter ([nf-core/tools#1415](https://github.com/nf-core/tools/issues/1415))
- Add pipeline description and authors between triple quotes to avoid errors with apostrophes ([#2066](https://github.com/nf-core/tools/pull/2066), [#2104](https://github.com/nf-core/tools/pull/2104))

### General

- Updated `nf-core download` to work with latest DSL2 syntax for containers ([#1379](https://github.com/nf-core/tools/issues/1379))
- Made `nf-core modules create` detect repository type with explicit `.nf-core.yml` instead of random readme stuff ([#1391](https://github.com/nf-core/tools/pull/1391))
- Added a Gitpod environment and Dockerfile ([#1384](https://github.com/nf-core/tools/pull/1384))
  - Adds conda, Nextflow, nf-core, pytest-workflow, mamba, and pip to base Gitpod Docker image.
  - Adds GH action to build and push Gitpod Docker image.
  - Adds Gitpod environment to template.
  - Adds Gitpod environment to tools with auto build of nf-core tool.
- Shiny new command-line help formatting ([#1403](https://github.com/nf-core/tools/pull/1403))
- Call the command line help with `-h` as well as `--help` (was formerly just the latter) ([#1404](https://github.com/nf-core/tools/pull/1404))
- Add `.yamllint.yml` config file to avoid line length and document start errors in the tools repo itself.
- Switch to `yamllint-github-action`to be able to configure yaml lint exceptions ([#1404](https://github.com/nf-core/tools/issues/1413))
- Prevent module linting KeyError edge case ([#1321](https://github.com/nf-core/tools/issues/1321))
- Bump-versions: Don't trim the trailing newline on files, causes editorconfig linting to fail ([#1265](https://github.com/nf-core/tools/issues/1265))
- Handle exception in `nf-core list` when a broken git repo is found ([#1273](https://github.com/nf-core/tools/issues/1273))
- Updated URL for pipeline lint test docs ([#1348](https://github.com/nf-core/tools/issues/1348))
- Updated `nf-core create` to tolerate failures and retry when fetching pipeline logos from the website ([#1369](https://github.com/nf-core/tools/issues/1369))
- Modified the CSS overriding `sphinx_rtd_theme` default colors to fix some glitches in the API documentation ([#1294](https://github.com/nf-core/tools/issues/1294))

### Modules

- New command `nf-core modules info` that prints nice documentation about a module to the terminal :sparkles: ([#1427](https://github.com/nf-core/tools/issues/1427))
- Linting a pipeline now fails instead of warning if a local copy of a module does not match the remote ([#1313](https://github.com/nf-core/tools/issues/1313))
- Fixed linting bugs where warning was incorrectly generated for:
  - `Module does not emit software version`
  - `Container versions do not match`
  - `input:` / `output:` not being specified in module
  - Allow for containers from other biocontainers resource as defined [here](https://github.com/nf-core/modules/blob/cde237e7cec07798e5754b72aeca44efe89fc6db/modules/cat/fastq/main.nf#L7-L8)
- Fixed traceback when using `stageAs` syntax as defined [here](https://github.com/nf-core/modules/blob/cde237e7cec07798e5754b72aeca44efe89fc6db/modules/cat/fastq/main.nf#L11)
- Added `nf-core schema docs` command to output pipeline parameter documentation in Markdown format for inclusion in GitHub and other documentation systems ([#741](https://github.com/nf-core/tools/issues/741))
- Allow conditional process execution from the configuration file ([#1393](https://github.com/nf-core/tools/pull/1393))
- Add linting for when condition([#1397](https://github.com/nf-core/tools/pull/1397))
- Added modules ignored table to `nf-core modules bump-versions`. ([#1234](https://github.com/nf-core/tools/issues/1234))
- Added `--conda-package-version` flag for specifying version of conda package in `nf-core modules create`. ([#1238](https://github.com/nf-core/tools/issues/1238))
- Add option of writing diffs to file in `nf-core modules update` using either interactive prompts or the new `--diff-file` flag.
- Fixed edge case where module names that were substrings of other modules caused both to be installed ([#1380](https://github.com/nf-core/tools/issues/1380))
- Tweak handling of empty files when generating the test YAML ([#1376](https://github.com/nf-core/tools/issues/1376))
  - Fail linting if a md5sum for an empty file is found (instead of a warning)
  - Don't skip the md5 when generating a test file if an empty file is found (so that linting fails and can be manually checked)
- Linting checks test files for `TODO` statements as well as the main module code ([#1271](https://github.com/nf-core/tools/issues/1271))
- Handle error if `manifest` isn't set in `nextflow.config` ([#1418](https://github.com/nf-core/tools/issues/1418))

## [v2.2 - Lead Liger](https://github.com/nf-core/tools/releases/tag/2.2) - [2021-12-14]

### Template

- Update repo logos to utilize [GitHub's `#gh-light/dark-mode-only`](https://docs.github.com/en/github/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#specifying-the-theme-an-image-is-shown-to), to switch between logos optimized for light or dark themes. The old repo logos have to be removed (in `docs/images` and `assets/`).
- Deal with authentication with private repositories
- Bump minimum Nextflow version to 21.10.3
- Convert pipeline template to updated Nextflow DSL2 syntax
- Solve circular import when importing `nf_core.modules.lint`
- Disable cache in `nf_core.utils.fetch_wf_config` while performing `test_wf_use_local_configs`.
- Modify software version channel handling to support multiple software version emissions (e.g. from mulled containers), and multiple software versions.
- Update `dumpsoftwareversion` module to correctly report versions with trailing zeros.
- Remove `params.hostnames` from the pipeline template ([#1304](https://github.com/nf-core/tools/issues/1304))
- Update `.gitattributes` to mark installed modules and subworkflows as `linguist-generated` ([#1311](https://github.com/nf-core/tools/issues/1311))
- Adding support for [Julia](https://julialang.org) package environments to `nextflow.config`([#1317](https://github.com/nf-core/tools/pull/1317))
- New YAML issue templates for pipeline bug reports and feature requests, with a much richer interface ([#1165](https://github.com/nf-core/tools/pull/1165))
- Update AWS test GitHub Actions to use v2 of [nf-core/tower-action](https://github.com/nf-core/tower-action)
- Post linting comment even when `linting.yml` fails
- Update `CONTRIBUTION.md` bullets to remove points related to `scrape_software_versions.py`
- Update AWS test to set Nextflow version to 21.10.3

### General

- Made lint check for parameters defaults stricter [[#992](https://github.com/nf-core/tools/issues/992)]
  - Default values in `nextflow.config` must match the defaults given in the schema (anything with `{` in, or in `main.nf` is ignored)
  - Defaults in `nextflow.config` must now match the variable _type_ specified in the schema
  - If you want the parameter to not have a default value, use `null`
  - Strings set to `false` or an empty string in `nextflow.config` will now fail linting
- Bump minimum Nextflow version to 21.10.3
- Changed `questionary` `ask()` to `unsafe_ask()` to not catch `KeyboardInterrupts` ([#1237](https://github.com/nf-core/tools/issues/1237))
- Fixed bug in `nf-core launch` due to revisions specified with `-r` not being added to nextflow command. ([#1246](https://github.com/nf-core/tools/issues/1246))
- Update regex in `readme` test of `nf-core lint` to agree with the pipeline template ([#1260](https://github.com/nf-core/tools/issues/1260))
- Update 'fix' message in `nf-core lint` to conform to the current command line options. ([#1259](https://github.com/nf-core/tools/issues/1259))
- Fixed bug in `nf-core list` when `NXF_HOME` is set
- Run CI test used to create and lint/run the pipeline template with minimum and latest edge release of NF ([#1304](https://github.com/nf-core/tools/issues/1304))
- New YAML issue templates for tools bug reports and feature requests, with a much richer interface ([#1165](https://github.com/nf-core/tools/pull/1165))
- Handle syntax errors in Nextflow config nicely when running `nf-core schema build` ([#1267](https://github.com/nf-core/tools/pull/1267))
- Erase temporary files and folders while performing Python tests (pytest)
- Remove base `Dockerfile` used for DSL1 pipeline container builds
- Run tests with Python 3.10
- [#1363](https://github.com/nf-core/tools/pull/1363) Fix tools CI workflow nextflow versions.

### Modules

- Fixed typo in `modules_utils.py`.
- Fixed failing lint test when process section was missing from module. Also added the local failing tests to the warned section of the output table. ([#1235](https://github.com/nf-core/tools/issues/1235))
- Added `--diff` flag to `nf-core modules update` which shows the diff between the installed files and the versions
- Update `nf-core modules create` help texts which were not changed with the introduction of the `--dir` flag
- Check if README is from modules repo
- Update module template to DSL2 v2.0 (remove `functions.nf` from modules template and updating `main.nf` ([#1289](https://github.com/nf-core/tools/pull/))
- Substitute get process/module name custom functions in module `main.nf` using template replacement ([#1284](https://github.com/nf-core/tools/issues/1284))
- Check test YML file for md5sums corresponding to empty files ([#1302](https://github.com/nf-core/tools/issues/1302))
- Exit with an error if empty files are found when generating the test YAML file ([#1302](https://github.com/nf-core/tools/issues/1302))

## [v2.1 - Zinc Zebra](https://github.com/nf-core/tools/releases/tag/2.1) - [2021-07-27]

### Template

- Correct regex pattern for file names in `nextflow_schema.json`
- Remove `.` from nf-core/tools command examples
- Update Nextflow installation link in pipeline template ([#1201](https://github.com/nf-core/tools/issues/1201))
- Command `hostname` is not portable [[#1212](https://github.com/nf-core/tools/pull/1212)]
- Changed how singularity and docker links are written in template to avoid duplicate links

### General

- Changed names of some flags with `-r` as short options to make the flags more consistent between commands.

### Modules

- Added consistency checks between installed modules and `modules.json` ([#1199](https://github.com/nf-core/tools/issues/1199))
- Added support excluding or specifying version of modules in `.nf-core.yml` when updating with `nf-core modules install --all` ([#1204](https://github.com/nf-core/tools/issues/1204))
- Created `nf-core modules update` and removed updating options from `nf-core modules install`
- Added missing function call to `nf-core lint` ([#1198](https://github.com/nf-core/tools/issues/1198))
- Fix `nf-core lint` not filtering modules test when run with `--key` ([#1203](https://github.com/nf-core/tools/issues/1203))
- Fixed `nf-core modules install` not working when installing from branch with `-b` ([#1218](https://github.com/nf-core/tools/issues/1218))
- Added prompt to choose between updating all modules or named module in `nf-core modules update`
- Check if modules is installed before trying to update in `nf-core modules update`
- Verify that a commit SHA provided with `--sha` exists for `install/update` commands
- Add new-line to `main.nf` after `bump-versions` command to make ECLint happy

## [v2.0.1 - Palladium Platypus Junior](https://github.com/nf-core/tools/releases/tag/2.0.1) - [2021-07-13]

### Template

- Critical tweak to add `--dir` declaration to `nf-core lint` GitHub Actions `linting.yml` workflow

### General

- Add `--dir` declaration to `nf-core sync` GitHub Actions `sync.yml` workflow

## [v2.0 - Palladium Platypus](https://github.com/nf-core/tools/releases/tag/2.0) - [2021-07-13]

### :warning: Major enhancements & breaking changes

This marks the first Nextflow DSL2-centric release of `tools` which means that some commands won't work in full with DSL1 pipelines anymore. Please use a `v1.x` version of `tools` for such pipelines or better yet join us to improve our DSL2 efforts! Here are the most important changes:

- The pipeline template has been completely re-written in DSL2
- A module template has been added to auto-create best-practice DSL2 modules to speed up development
- A whole suite of commands have been added to streamline the creation, installation, removal, linting and version bumping of DSL2 modules either installed within pipelines or the nf-core/modules repo

### Template

- Move TODO item of `contains:` map in a YAML string [[#1082](https://github.com/nf-core/tools/issues/1082)]
- Trigger AWS tests via Tower API [[#1160](https://github.com/nf-core/tools/pull/1160)]

### General

- Fixed a bug in the Docker image build for tools that failed due to an extra hyphen. [[#1069](https://github.com/nf-core/tools/pull/1069)]
- Regular release sync fix - this time it was to do with JSON serialisation [[#1072](https://github.com/nf-core/tools/pull/1072)]
- Fixed bug in schema validation that ignores upper/lower-case typos in parameters [[#1087](https://github.com/nf-core/tools/issues/1087)]
- Bugfix: Download should use path relative to workflow for configs
- Remove lint checks for files related to conda and docker as not needed anymore for DSL2
- Removed `params_used` lint check because of incompatibility with DSL2
- Added`modules bump-versions` command to `README.md`
- Update docs for v2.0 release

### Modules

- Update comment style of modules `functions.nf` template file [[#1076](https://github.com/nf-core/tools/issues/1076)]
- Changed working directory to temporary directory for `nf-core modules create-test-yml` [[#908](https://github.com/nf-core/tools/issues/908)]
- Use Biocontainers API instead of quayi.io API for `nf-core modules create` [[#875](https://github.com/nf-core/tools/issues/875)]
- Update `nf-core modules install` to handle different versions of modules [#1116](https://github.com/nf-core/tools/pull/1116)
- Added `nf-core modules bump-versions` command to update all versions in the `nf-core/modules` repository [[#1123](https://github.com/nf-core/tools/issues/1123)]
- Updated `nf-core modules lint` to check whether a `git_sha` exists in the `modules.json` file or whether a new version is available [[#1114](https://github.com/nf-core/tools/issues/1114)]
- Refactored `nf-core modules` command into one file per command [#1124](https://github.com/nf-core/tools/pull/1124)
- Updated `nf-core modules remove` to also remove entry in `modules.json` file ([#1115](https://github.com/nf-core/tools/issues/1115))
- Bugfix: Interactive prompt for `nf-core modules install` was receiving too few arguments
- Added progress bar to creation of 'modules.json'
- Updated `nf-core modules list` to show versions of local modules
- Improved exit behavior by replacing `sys.exit` with exceptions
- Updated `nf-core modules remove` to remove module entry in `modules.json` if module directory is missing
- Create extra tempdir as work directory for `nf-core modules create-test-yml` to avoid adding the temporary files to the `test.yml`
- Refactored passing of command line arguments to `nf-core` commands and subcommands ([#1139](https://github.com/nf-core/tools/issues/1139), [#1140](https://github.com/nf-core/tools/issues/1140))
- Check for `modules.json` for entries of modules that are not actually installed in the pipeline [[#1141](https://github.com/nf-core/tools/issues/1141)]
- Added `<keywords>` argument to `nf-core modules list` for filtering the listed modules. ([#1139](https://github.com/nf-core/tools/issues/1139)
- Added support for a `bump-versions` configuration file [[#1142](https://github.com/nf-core/tools/issues/1142)]
- Fixed `nf-core modules create-test-yml` so it doesn't break when the output directory is supplied [[#1148](https://github.com/nf-core/tools/issues/1148)]
- Updated `nf-core modules lint` to work with new directory structure [[#1159](https://github.com/nf-core/tools/issues/1159)]
- Updated `nf-core modules install` and `modules.json` to work with new directory structure ([#1159](https://github.com/nf-core/tools/issues/1159))
- Updated `nf-core modules remove` to work with new directory structure [[#1159](https://github.com/nf-core/tools/issues/1159)]
- Restructured code and removed old table style in `nf-core modules list`
- Fixed bug causing `modules.json` creation to loop indefinitely
- Added `--all` flag to `nf-core modules install`
- Added `remote` and `local` subcommands to `nf-core modules list`
- Fix bug due to restructuring in modules template
- Added checks for verifying that the remote repository is well formed
- Added checks to `ModulesCommand` for verifying validity of remote repositories
- Misc. changes to `modules install`: check that module exist in remote, `--all` is has `--latest` by default.

#### Sync

- Don't set the default value to `"null"` when a parameter is initialised as `null` in the config [[#1074](https://github.com/nf-core/tools/pull/1074)]

#### Tests

- Added a test for the `version_consistency` lint check
- Refactored modules tests into separate files, and removed direct comparisons with number of tests in `lint` tests ([#1158](https://github.com/nf-core/tools/issues/1158))

## [v1.14 - Brass Chicken :chicken:](https://github.com/nf-core/tools/releases/tag/1.14) - [2021-05-11]

### Template

- Add the implicit workflow declaration to `main.nf` DSL2 template [[#1056](https://github.com/nf-core/tools/issues/1056)]
- Fixed an issue regarding explicit disabling of unused container engines [[#972](https://github.com/nf-core/tools/pull/972)]
- Removed trailing slash from `params.igenomes_base` to yield valid s3 paths (previous paths work with Nextflow but not aws cli)
- Added a timestamp to the trace + timetime + report + dag filenames to fix overwrite issue on AWS
- Rewrite the `params_summary_log()` function to properly ignore unset params and have nicer formatting [[#971](https://github.com/nf-core/tools/issues/971)]
- Fix overly strict `--max_time` formatting regex in template schema [[#973](https://github.com/nf-core/tools/issues/973)]
- Convert `d` to `day` in the `cleanParameters` function to make Duration objects like `2d` pass the validation [[#858](https://github.com/nf-core/tools/issues/858)]
- Added nextflow version to quick start section and adjusted `nf-core bump-version` [[#1032](https://github.com/nf-core/tools/issues/1032)]
- Use latest stable Nextflow version `21.04.0` for CI tests instead of the `-edge` release

### Download

- Fix bug in `nf-core download` where image names were getting a hyphen in `nf-core` which was breaking things.
- Extensive new interactive prompts for all command line flags [[#1027](https://github.com/nf-core/tools/issues/1027)]
  - It is now recommended to run `nf-core download` without any cli options and follow prompts (though flags can be used to run non-interactively if you wish)
- New helper code to set `$NXF_SINGULARITY_CACHEDIR` and add to `.bashrc` if desired [[#1027](https://github.com/nf-core/tools/issues/1027)]

### Launch

- Strip values from `nf-core launch` web response which are `False` and have no default in the schema [[#976](https://github.com/nf-core/tools/issues/976)]
- Improve API caching code when polling the website, fixes noisy log message when waiting for a response [[#1029](https://github.com/nf-core/tools/issues/1029)]
- New interactive prompts for pipeline name [[#1027](https://github.com/nf-core/tools/issues/1027)]

### Modules

- Added `tool_name_underscore` to the module template to allow TOOL_SUBTOOL in `main.nf` [[#1011](https://github.com/nf-core/tools/issues/1011)]
- Added `--conda-name` flag to `nf-core modules create` command to allow sidestepping questionary [[#988](https://github.com/nf-core/tools/issues/988)]
- Extended `nf-core modules lint` functionality to check tags in `test.yml` and to look for a entry in the `pytest_software.yml` file
- Update `modules` commands to use new test tag format `tool/subtool`
- New modules lint test comparing the `functions.nf` file to the template version
- Modules installed from alternative sources are put in folders based on the name of the source repository

### Linting

- Fix bug in nf-core lint config skipping for the `nextflow_config` test [[#1019](https://github.com/nf-core/tools/issues/1019)]
- New `-k`/`--key` cli option for `nf-core lint` to allow you to run only named lint tests, for faster local debugging
- Merge markers lint test - ignore binary files, allow config to ignore specific files [[#1040](https://github.com/nf-core/tools/pull/1040)]
- New lint test to check if all defined pipeline parameters are mentioned in `main.nf` [[#1038](https://github.com/nf-core/tools/issues/1038)]
- Added fix to remove warnings about params that get converted from camelCase to camel-case [[#1035](https://github.com/nf-core/tools/issues/1035)]
- Added pipeline schema lint checks for missing parameter description and parameters outside of groups [[#1017](https://github.com/nf-core/tools/issues/1017)]

### General

- Try to fix the fix for the automated sync when we submit too many PRs at once [[#970](https://github.com/nf-core/tools/issues/970)]
- Rewrite how the tools documentation is deployed to the website, to allow multiple versions
- Created new Docker image for the tools cli package - see installation docs for details [[#917](https://github.com/nf-core/tools/issues/917)]
- Ignore permission errors for setting up requests cache directories to allow starting with an invalid or read-only `HOME` directory

## [v1.13.3 - Copper Crocodile Resurrection :crocodile:](https://github.com/nf-core/tools/releases/tag/1.13.2) - [2021-03-24]

- Running tests twice with `nf-core modules create-test-yml` to catch unreproducible md5 sums [[#890](https://github.com/nf-core/tools/issues/890)]
- Fix sync error again where the Nextflow edge release needs to be used for some pipelines
- Fix bug with `nf-core lint --release` (`NameError: name 'os' is not defined`)
- Added linebreak to linting comment so that markdown header renders on PR comment properly
- `nf-core modules create` command - if no bioconda package is found, prompt user for a different bioconda package name
- Updated module template `main.nf` with new test data paths

## [v1.13.2 - Copper Crocodile CPR :crocodile: :face_with_head_bandage:](https://github.com/nf-core/tools/releases/tag/1.13.2) - [2021-03-23]

- Make module template pass the EC linter [[#953](https://github.com/nf-core/tools/pull/953)]
- Added better logging message if a user doesn't specify the directory correctly with `nf-core modules` commands [[#942](https://github.com/nf-core/tools/pull/942)]
- Fixed parameter validation bug caused by JSONObject [[#937](https://github.com/nf-core/tools/issues/937)]
- Fixed template creation error regarding file permissions [[#932](https://github.com/nf-core/tools/issues/932)]
- Split the `create-lint-wf` tests up into separate steps in GitHub Actions to make the CI results easier to read
- Added automated PR comments to the Markdown, YAML and Python lint CI tests to explain failures (tools and pipeline template)
- Make `nf-core lint` summary table borders coloured according to overall pass / fail status
- Attempted a fix for the automated sync when we submit too many PRs at once [[#911](https://github.com/nf-core/tools/issues/911)]

## [v1.13.1 - Copper Crocodile Patch :crocodile: :pirate_flag:](https://github.com/nf-core/tools/releases/tag/1.13.1) - [2021-03-19]

- Fixed bug in pipeline linting markdown output that gets posted to PR comments [[#914]](https://github.com/nf-core/tools/issues/914)
- Made text for the PR branch CI check less verbose with a TLDR in bold at the top
- A number of minor tweaks to the new `nf-core modules lint` code

## [v1.13 - Copper Crocodile](https://github.com/nf-core/tools/releases/tag/1.13) - [2021-03-18]

### Template

- **Major new feature** - Validation of pipeline parameters [[#426]](https://github.com/nf-core/tools/issues/426)
  - The addition runs as soon as the pipeline launches and checks the pipeline input parameters two main things:
    - No parameters are supplied that share a name with core Nextflow options (eg. `--resume` instead of `-resume`)
    - Supplied parameters validate against the pipeline JSON schema (eg. correct variable types, required values)
  - If either parameter validation fails or the pipeline has errors, a warning is given about any unexpected parameters found which are not described in the pipeline schema.
  - This behaviour can be disabled by using `--validate_params false`
- Added profiles to support the [Charliecloud](https://hpc.github.io/charliecloud/) and [Shifter](https://nersc.gitlab.io/development/shifter/how-to-use/) container engines [[#824](https://github.com/nf-core/tools/issues/824)]
  - Note that Charliecloud requires Nextflow version `v21.03.0-edge` or later.
- Profiles for container engines now explicitly _disable_ all other engines [[#867](https://github.com/nf-core/tools/issues/867)]
- Fixed typo in nf-core-lint CI that prevented the markdown summary from being automatically posted on PRs as a comment.
- Changed default for `--input` from `data/*{1,2}.fastq.gz` to `null`, as this is now validated by the schema as a required value.
- Removed support for `--name` parameter for custom run names.
  - The same functionality for MultiQC still exists with the core Nextflow `-name` option.
- Added to template docs about how to identify process name for resource customisation
- The parameters `--max_memory` and `--max_time` are now validated against a regular expression [[#793](https://github.com/nf-core/tools/issues/793)]
  - Must be written in the format `123.GB` / `456.h` with any of the prefixes listed in the [Nextflow docs](https://www.nextflow.io/docs/latest/process.html#memory)
  - Bare numbers no longer allowed, avoiding people from trying to specify GB and actually specifying bytes.
- Switched from cookiecutter to Jinja2 [[#880]](https://github.com/nf-core/tools/pull/880)
- Finally dropped the wonderful [cookiecutter](https://github.com/cookiecutter/cookiecutter) library that was behind the first pipeline template that led to nf-core [[#880](https://github.com/nf-core/tools/pull/880)]
  - Now rendering templates directly using [Jinja](https://jinja.palletsprojects.com/), which is what cookiecutter was doing anyway

### Modules

Initial addition of a number of new helper commands for working with DSL2 modules:

- `modules list` - List available modules
- `modules install` - Install a module from nf-core/modules
- `modules remove` - Remove a module from a pipeline
- `modules create` - Create a module from the template
- `modules create-test-yml` - Create the `test.yml` file for a module with md5 sums, tags, commands and names added
- `modules lint` - Check a module against nf-core guidelines

You can read more about each of these commands in the main tools documentation (see `README.md` or <https://nf-co.re/tools>)

### Tools helper code

- Fixed some bugs in the command line interface for `nf-core launch` and improved formatting [[#829](https://github.com/nf-core/tools/pull/829)]
- New functionality for `nf-core download` to make it compatible with DSL2 pipelines [[#832](https://github.com/nf-core/tools/pull/832)]
  - Singularity images in module files are now discovered and fetched
  - Direct downloads of Singularity images in python allowed (much faster than running `singularity pull`)
  - Downloads now work with `$NXF_SINGULARITY_CACHEDIR` so that pipelines sharing containers have efficient downloads
- Changed behaviour of `nf-core sync` command [[#787](https://github.com/nf-core/tools/issues/787)]
  - Instead of opening or updating a PR from `TEMPLATE` directly to `dev`, a new branch is now created from `TEMPLATE` and a PR opened from this to `dev`.
  - This is to make it easier to fix merge conflicts without accidentally bringing the entire pipeline history back into the `TEMPLATE` branch (which makes subsequent sync merges much more difficult)

### Linting

- Major refactor and rewrite of pipieline linting code
  - Much better code organisation and maintainability
  - New automatically generated documentation using Sphinx
  - Numerous new tests and functions, removal of some unnecessary tests
- Added lint check for merge markers [[#321]](https://github.com/nf-core/tools/issues/321)
- Added new option `--fix` to automatically correct some problems detected by linting
- Added validation of default params to `nf-core schema lint` [[#823](https://github.com/nf-core/tools/issues/823)]
- Added schema validation of GitHub action workflows to lint function [[#795](https://github.com/nf-core/tools/issues/795)]
- Fixed bug in schema title and description validation
- Added second progress bar for conda dependencies lint check, as it can be slow [[#299](https://github.com/nf-core/tools/issues/299)]
- Added new lint test to check files that should be unchanged from the pipeline.
- Added the possibility to ignore lint tests using a `nf-core-lint.yml` config file [[#809](https://github.com/nf-core/tools/pull/809)]

## [v1.12.1 - Silver Dolphin](https://github.com/nf-core/tools/releases/tag/1.12.1) - [2020-12-03]

### Template

- Finished switch from `$baseDir` to `$projectDir` in `iGenomes.conf` and `main.nf`
  - Main fix is for `smail_fields` which was a bug introduced in the previous release. Sorry about that!
- Ported a number of small content tweaks from nf-core/eager to the template [[#786](https://github.com/nf-core/tools/issues/786)]
  - Better contributing documentation, more placeholders in documentation files, more relaxed markdownlint exceptions for certain HTML tags, more content for the PR and issue templates.

### Tools helper code

- Pipeline schema: make parameters of type `range` to `number`. [[#738](https://github.com/nf-core/tools/issues/738)]
- Respect `$NXF_HOME` when looking for pipelines with `nf-core list` [[#798](https://github.com/nf-core/tools/issues/798)]
- Swapped PyInquirer with questionary for command line questions in `launch.py` [[#726](https://github.com/nf-core/tools/issues/726)]
  - This should fix conda installation issues that some people had been hitting
  - The change also allows other improvements to the UI
- Fix linting crash when a file deleted but not yet staged in git [[#796](https://github.com/nf-core/tools/issues/796)]

## [v1.12 - Mercury Weasel](https://github.com/nf-core/tools/releases/tag/1.12) - [2020-11-19]

### Tools helper code

- Updated `nf_core` documentation generator for building [https://nf-co.re/tools-docs/](https://nf-co.re/tools-docs/)

### Template

- Make CI comments work with PRs from forks [[#765](https://github.com/nf-core/tools/issues/765)]
  - Branch protection and linting results should now show on all PRs
- Updated GitHub issue templates, which had stopped working
- Refactored GitHub Actions so that the AWS full-scale tests are triggered after docker build is finished
  - DockerHub push workflow split into two - one for dev, one for releases
- Updated actions to no longer use `set-env` which is now depreciating [[#739](https://github.com/nf-core/tools/issues/739)]
- Added config import for `test_full` in `nextflow.config`
- Switched depreciated `$baseDir` to `$projectDir`
- Updated minimum Nextflow version to `20.04.10`
- Make Nextflow installation less verbose in GitHub Actions [[#780](https://github.com/nf-core/tools/pull/780)]

### Linting

- Updated code to display colours in GitHub Actions log output
- Allow tests to pass with `dev` version of nf-core/tools (previous failure due to base image version)
- Lint code no longer tries to post GitHub PR comments. This is now done in a GitHub Action only.

## [v1.11 - Iron Tiger](https://github.com/nf-core/tools/releases/tag/1.11) - [2020-10-27]

### Template

- Fix command error in `awstest.yml` GitHub Action workflow.
- Allow manual triggering of AWS test GitHub Action workflows.
- Remove TODO item, which was proposing the usage of additional files beside `usage.md` and `output.md` for documentation.
- Added a Podman profile, which enables Podman as container.
- Updated linting for GitHub actions AWS tests workflows.

### Linting

- Made a base-level `Dockerfile` a warning instead of failure
- Added a lint failure if the old `bin/markdown_to_html.r` script is found
- Update `rich` package dependency and use new markup escaping to change `[[!]]` back to `[!]` again

### Other

- Pipeline sync - fetch full repo when checking out before sync
- Sync - Add GitHub actions manual trigger option

## [v1.10.2 - Copper Camel _(brought back from the dead)_](https://github.com/nf-core/tools/releases/tag/1.10.2) - [2020-07-31]

Second patch release to address some small errors discovered in the pipeline template.
Apologies for the inconvenience.

- Fix syntax error in `/push_dockerhub.yml` GitHub Action workflow
- Change `params.readPaths` -> `params.input_paths` in `test_full.config`
- Check results when posting the lint results as a GitHub comment
  - This feature is unfortunately not possible when making PRs from forks outside of the nf-core organisation for now.
- More major refactoring of the automated pipeline sync
  - New GitHub Actions matrix parallelisation of sync jobs across pipelines [[#673](https://github.com/nf-core/tools/issues/673)]
  - Removed the `--all` behaviour from `nf-core sync` as we no longer need it
  - Sync now uses a new list of pipelines on the website which does not include archived pipelines [[#712](https://github.com/nf-core/tools/issues/712)]
  - When making a PR it checks if a PR already exists - if so it updates it [[#710](https://github.com/nf-core/tools/issues/710)]
  - More tests and code refactoring for more stable code. Hopefully fixes 404 error [[#711](https://github.com/nf-core/tools/issues/711)]

## [v1.10.1 - Copper Camel _(patch)_](https://github.com/nf-core/tools/releases/tag/1.10.1) - [2020-07-30]

Patch release to fix the automatic template synchronisation, which failed in the v1.10 release.

- Improved logging: `nf-core --log-file log.txt` now saves a verbose log to disk.
- nf-core/tools GitHub Actions pipeline sync now uploads verbose log as an artifact.
- Sync - fixed several minor bugs, made logging less verbose.
- Python Rich library updated to `>=4.2.1`
- Hopefully fix git config for pipeline sync so that commit comes from @nf-core-bot
- Fix sync auto-PR text indentation so that it doesn't all show as code
- Added explicit flag `--show-passed` for `nf-core lint` instead of taking logging verbosity

## [v1.10 - Copper Camel](https://github.com/nf-core/tools/releases/tag/1.10) - [2020-07-30]

### Pipeline schema

This release of nf-core/tools introduces a major change / new feature: pipeline schema.
These are [JSON Schema](https://json-schema.org/) files that describe all of the parameters for a given
pipeline with their ID, a description, a longer help text, an optional default value, a variable _type_
(eg. `string` or `boolean`) and more.

The files will be used in a number of places:

- Automatic validation of supplied parameters when running pipelines
  - Pipeline execution can be immediately stopped if a required `param` is missing,
    or does not conform to the patterns / allowed values in the schema.
- Generation of pipeline command-line help
  - Running `nextflow run <pipeline> --help` will use the schema to generate a help text automatically
- Building online documentation on the [nf-core website](https://nf-co.re)
- Integration with 3rd party graphical user interfaces

To support these new schema files, nf-core/tools now comes with a new set of commands: `nf-core schema`.

- Pipeline schema can be generated or updated using `nf-core schema build` - this takes the parameters from
  the pipeline config file and prompts the developer for any mismatch between schema and pipeline.
  - Once a skeleton Schema file has been built, the command makes use of a new nf-core website tool to provide
    a user friendly graphical interface for developers to add content to their schema: [https://nf-co.re/pipeline_schema_builder](https://nf-co.re/pipeline_schema_builder)
- Pipelines will be automatically tested for valid schema that describe all pipeline parameters using the
  `nf-core schema lint` command (also included as part of the main `nf-core lint` command).
- Users can validate their set of pipeline inputs using the `nf-core schema validate` command.

In addition to the new schema commands, the `nf-core launch` command has been completely rewritten from
scratch to make use of the new pipeline schema. This command can use either an interactive command-line
prompt or a rich web interface to help users set parameters for a pipeline run.

The parameter descriptions and help text are fully used and embedded into the launch interfaces to make
this process as user-friendly as possible. We hope that it's particularly well suited to those new to nf-core.

Whilst we appreciate that this new feature will add a little work for pipeline developers, we're excited at
the possibilities that it brings. If you have any feedback or suggestions, please let us know either here on
GitHub or on the nf-core [`#json-schema` Slack channel](https://nfcore.slack.com/channels/json-schema).

### Python code formatting

We have adopted the use of the [Black Python code formatter](https://black.readthedocs.io/en/stable/).
This ensures a harmonised code formatting style throughout the package, from all contributors.
If you are editing any Python code in nf-core/tools you must now pass the files through Black when
making a pull-request. See [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) for details.

### Template

- Add `--publish_dir_mode` parameter [#585](https://github.com/nf-core/tools/issues/585)
- Isolate R library paths to those in container [#541](https://github.com/nf-core/tools/issues/541)
- Added new style of pipeline parameters JSON schema to pipeline template
- Add ability to attach MultiQC reports to completion emails when using `mail`
- Update `output.md` and add in 'Pipeline information' section describing standard NF and pipeline reporting.
- Build Docker image using GitHub Actions, then push to Docker Hub (instead of building on Docker Hub)
- Add Slack channel badge in pipeline README
- Allow multiple container tags in `ci.yml` if performing multiple tests in parallel
- Add AWS CI tests and full tests GitHub Actions workflows
- Update AWS CI tests and full tests secrets names
- Added `macs_gsize` for danRer10, based on [this post](https://biostar.galaxyproject.org/p/18272/)
- Add information about config files used for workflow execution (`workflow.configFiles`) to summary
- Fix `markdown_to_html.py` to work with Python 2 and 3.
- Change `params.reads` -> `params.input`
- Adding TODOs and MultiQC process in DSL2 template
- Change `params.readPaths` -> `params.input_paths`
- Added a `.github/.dockstore.yml` config file for automatic workflow registration with [dockstore.org](https://dockstore.org/)

### Linting

- Refactored PR branch tests to be a little clearer.
- Linting error docs explain how to add an additional branch protection rule to the `branch.yml` GitHub Actions workflow.
- Adapted linting docs to the new PR branch tests.
- Failure for missing the readme bioconda badge is now a warn, in case this badge is not relevant
- Added test for template `{{ cookiecutter.var }}` placeholders
- Fix failure when providing version along with build id for Conda packages
- New `--json` and `--markdown` options to print lint results to JSON / markdown files
- Linting code now automatically posts warning / failing results to GitHub PRs as a comment if it can
- Added AWS GitHub Actions workflows linting
- Fail if `params.input` isn't defined.
- Beautiful new progress bar to look at whilst linting is running and awesome new formatted output on the command line :heart_eyes:
  - All made using the excellent [`rich` python library](https://github.com/willmcgugan/rich) - check it out!
- Tests looking for `TODO` strings should now ignore editor backup files. [#477](https://github.com/nf-core/tools/issues/477)

### nf-core/tools Continuous Integration

- Added CI test to check for PRs against `master` in tools repo
- CI PR branch tests fixed & now automatically add a comment on the PR if failing, explaining what is wrong
- Move some of the issue and PR templates into HTML `<!-- comments -->` so that they don't show in issues / PRs

### Other

- Describe alternative installation method via conda with `conda env create`
- nf-core/tools version number now printed underneath header artwork
- Bumped Conda version shipped with nfcore/base to 4.8.2
- Added log message when creating new pipelines that people should talk to the community about their plans
- Fixed 'on completion' emails sent using the `mail` command not containing body text.
- Improved command-line help text for nf-core/tools
- `nf-core list` now hides archived pipelines unless `--show_archived` flag is set
- Command line tools now checks if there is a new version of nf-core/tools available
  - Disable this by setting the environment variable `NFCORE_NO_VERSION_CHECK`, eg. `export NFCORE_NO_VERSION_CHECK=1`
- Better command-line output formatting of nearly all `nf-core` commands using [`rich`](https://github.com/willmcgugan/rich)

## [v1.9 - Platinum Pigeon](https://github.com/nf-core/tools/releases/tag/1.9) - [2020-02-20]

### Continuous integration

- Travis CI tests are now deprecated in favor of GitHub Actions within the pipeline template.
  - `nf-core bump-version` support has been removed for `.travis.yml`
  - `nf-core lint` now fails if a `.travis.yml` file is found
- Ported nf-core/tools Travis CI automation to GitHub Actions.
- Fixed the build for the nf-core/tools API documentation on the website

### Template

- Rewrote the documentation markdown > HTML conversion in Python instead of R
- Fixed rendering of images in output documentation [#391](https://github.com/nf-core/tools/issues/391)
- Removed the requirement for R in the conda environment
- Make `params.multiqc_config` give an _additional_ MultiQC config file instead of replacing the one that ships with the pipeline
- Ignore only `tests/` and `testing/` directories in `.gitignore` to avoid ignoring `test.config` configuration file
- Rephrase docs to promote usage of containers over Conda to ensure reproducibility
- Stage the workflow summary YAML file within MultiQC work directory

### Linting

- Removed linting for CircleCI
- Allow any one of `params.reads` or `params.input` or `params.design` before warning
- Added whitespace padding to lint error URLs
- Improved documentation for lint errors
- Allow either `>=` or `!>=` in nextflow version checks (the latter exits with an error instead of just warning) [#506](https://github.com/nf-core/tools/issues/506)
- Check that `manifest.version` ends in `dev` and throw a warning if not
  - If running with `--release` check the opposite and fail if not
- Tidied up error messages and syntax for linting GitHub actions branch tests
- Add YAML validator
- Don't print test results if we have a critical error

### Other

- Fix automatic synchronisation of the template after releases of nf-core/tools
- Improve documentation for installing `nf-core/tools`
- Replace preprint by the new nf-core publication in Nature Biotechnology :champagne:
- Use `stderr` instead of `stdout` for header artwork
- Tolerate unexpected output from `nextflow config` command
- Add social preview image
- Added a [release checklist](.github/RELEASE_CHECKLIST.md) for the tools repo

## [v1.8 - Black Sheep](https://github.com/nf-core/tools/releases/tag/1.8) - [2020-01-27]

### Continuous integration

- GitHub Actions CI workflows are now included in the template pipeline
  - Please update these files to match the existing tests that you have in `.travis.yml`
- Travis CI tests will be deprecated from the next `tools` release
- Linting will generate a warning if GitHub Actions workflows do not exist and if applicable to remove Travis CI workflow file i.e. `.travis.yml`.

### Tools helper code

- Refactored the template synchronisation code to be part of the main nf-core tool
- `nf-core bump-version` now also bumps the version string of the exported conda environment in the Dockerfile
- Updated Blacklist of synced pipelines
- Ignore pre-releases in `nf-core list`
- Updated documentation for `nf-core download`
- Fixed typo in `nf-core launch` final command
- Handle missing pipeline descriptions in `nf-core list`
- Migrate tools package CI to GitHub Actions

### Linting

- Adjusted linting to enable `patch` branches from being tested
- Warn if GitHub Actions workflows do not exist, warn if `.travis.yml` and circleCI are there
- Lint for `Singularity` file and raise error if found [#458](https://github.com/nf-core/tools/issues/458)
- Added linting of GitHub Actions workflows `linting.yml`, `ci.yml` and `branch.yml`
- Warn if pipeline name contains upper case letters or non alphabetical characters [#85](https://github.com/nf-core/tools/issues/85)
- Make CI tests of lint code pass for releases

### Template pipeline

- Fixed incorrect paths in iGenomes config as described in issue [#418](https://github.com/nf-core/tools/issues/418)
- Fixed incorrect usage of non-existent parameter in the template [#446](https://github.com/nf-core/tools/issues/446)
- Add UCSC genomes to `igenomes.config` and add paths to all genome indices
- Change `maxMultiqcEmailFileSize` parameter to `max_multiqc_email_size`
- Export conda environment in Docker file [#349](https://github.com/nf-core/tools/issues/349)
- Change remaining parameters from `camelCase` to `snake_case` [#39](https://github.com/nf-core/hic/issues/39)
  - `--singleEnd` to `--single_end`
  - `--igenomesIgnore` to `--igenomes_ignore`
  - Having the old camelCase versions of these will now throw an error
- Add `autoMounts=true` to default singularity profile
- Add in `markdownlint` checks that were being ignored by default
- Disable ansi logging in the travis CI tests
- Move `params`section from `base.config` to `nextflow.config`
- Use `env` scope to export `PYTHONNOUSERSITE` in `nextflow.config` to prevent conflicts with host Python environment
- Bump minimum Nextflow version to `19.10.0` - required to properly use `env` scope in `nextflow.config`
- Added support for nf-tower in the travis tests, using public mailbox <nf-core@mailinator.com>
- Add link to [Keep a Changelog](http://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](http://semver.org/spec/v2.0.0.html) to CHANGELOG
- Adjusted `.travis.yml` checks to allow for `patch` branches to be tested
- Add Python 3.7 dependency to the `environment.yml` file
- Remove `awsbatch` profile cf [nf-core/configs#71](https://github.com/nf-core/configs/pull/71)
- Make `scrape_software_versions.py` compatible with Python3 to enable miniconda3 in [base image PR](https://github.com/nf-core/tools/pull/462)
- Add GitHub Actions workflows and respective linting
- Add `NXF_ANSI_LOG` as global environment variable to template GitHub Actions CI workflow
- Fixed global environment variable in GitHub Actions CI workflow
- Add `--awscli` parameter
- Add `README.txt` path for genomes in `igenomes.config` [nf-core/atacseq#75](https://github.com/nf-core/atacseq/issues/75)
- Fix buggy ANSI codes in pipeline summary log messages
- Add a `TODO` line in the new GitHub Actions CI test files

### Base Docker image

- Use miniconda3 instead of miniconda for a Python 3k base environment
  - If you still need Python 2 for your pipeline, add `conda-forge::python=2.7.4` to the dependencies in your `environment.yml`
- Update conda version to 4.7.12

### Other

- Updated Base Dockerfile to Conda 4.7.10
- Entirely switched from Travis-Ci.org to Travis-Ci.com for template and tools
- Improved core documentation (`-profile`)

## [v1.7 - Titanium Kangaroo](https://github.com/nf-core/tools/releases/tag/1.7) - [2019-10-07]

### Tools helper code

- The tools `create` command now sets up a `TEMPLATE` and a `dev` branch for syncing
- Fixed issue [379](https://github.com/nf-core/tools/issues/379)
- nf-core launch now uses stable parameter schema version 0.1.0
- Check that PR from patch or dev branch is acceptable by linting
- Made code compatible with Python 3.7
- The `download` command now also fetches institutional configs from nf-core/configs
- When listing pipelines, a nicer message is given for the rare case of a detached `HEAD` ref in a locally pulled pipeline. [#297](https://github.com/nf-core/tools/issues/297)
- The `download` command can now compress files into a single archive.
- `nf-core create` now fetches a logo for the pipeline from the nf-core website
- The readme should now be rendered properly on PyPI.

### Syncing

- Can now sync a targeted pipeline via command-line
- Updated Blacklist of synced pipelines
- Removed `chipseq` from Blacklist of synced pipelines
- Fixed issue [#314](https://github.com/nf-core/tools/issues/314)

### Linting

- If the container slug does not contain the nf-core organisation (for example during development on a fork), linting will raise a warning, and an error with release mode on

### Template pipeline

- Add new code for Travis CI to allow PRs from patch branches too
- Fix small typo in central readme of tools for future releases
- Small code polishing + typo fix in the template main.nf file
- Header ANSI codes no longer print `[2m` to console when using `-with-ansi`
- Switched to yaml.safe_load() to fix PyYAML warning that was thrown because of a possible [exploit](<https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation>)
- Add `nf-core` citation
- Add proper `nf-core` logo for tools
- Add `Quick Start` section to main README of template
- Fix [Docker RunOptions](https://github.com/nf-core/tools/pull/351) to get UID and GID set in the template
- `Dockerfile` now specifically uses the proper release tag of the nfcore/base image
- Use [`file`](https://github.com/nf-core/tools/pull/354) instead of `new File`
  to avoid weird behavior such as making an `s3:/` directory locally when using
  an AWS S3 bucket as the `--outdir`.
- Fix workflow.onComplete() message when finishing pipeline
- Update URL for joining the nf-core slack to [https://nf-co.re/join/slack](https://nf-co.re/join/slack)
- Add GitHub Action for CI and Linting
- [Increased default time limit](https://github.com/nf-core/tools/issues/370) to 4h
- Add direct link to the pipeline slack channel in the contribution guidelines
- Add contributions and support heading with links to contribution guidelines and link to the pipeline slack channel in the main README
- Fix Parameters JSON due to new versionized structure
- Added conda-forge::r-markdown=1.1 and conda-forge::r-base=3.6.1 to environment
- Plain-text email template now has nf-core ASCII artwork
- Template configured to use logo fetched from website
- New option `--email_on_fail` which only sends emails if the workflow is not successful
- Add file existence check when checking software versions
- Fixed issue [#165](https://github.com/nf-core/tools/issues/165) - Use `checkIfExists`
- Consistent spacing for `if` statements
- Add sensible resource labels to `base.config`

### Other

- Bump `conda` to 4.6.14 in base nf-core Dockerfile
- Added a Code of Conduct to nf-core/tools, as only the template had this before
- TravisCI tests will now also start for PRs from `patch` branches, [to allow fixing critical issues](https://github.com/nf-core/tools/pull/392) without making a new major release

## [v1.6 - Brass Walrus](https://github.com/nf-core/tools/releases/tag/1.6) - [2020-04-09]

### Syncing

- Code refactoring to make the script more readable
- No travis build failure anymore on sync errors
- More verbose logging

### Template pipeline

- awsbatch `work-dir` checking moved to nextflow itself. Removed unsatisfiable check in main.nf template.
- Fixed markdown linting
- Tools CI testing now runs markdown lint on compiled template pipeline
- Migrated large portions of documentation to the [nf-core website](https://github.com/nf-core/nf-co.re/pull/93)
- Removed Gitter references in `.github/` directories for `tools/` and pipeline template.
- Changed `scrape_software_versions.py` to output `.csv` file
- Added `export_plots` parameter to multiqc config
- Corrected some typos as listed [here](https://github.com/nf-core/tools/issues/348) to Guidelines

### Tools helper code

- Drop [nf-core/rnaseq](https://github.com/nf-core/rnaseq]) from `blacklist.json` to make template sync available
- Updated main help command to sort the subcommands in a more logical order
- Updated readme to describe the new `nf-core launch` command
- Fix bugs in `nf-core download`
  - The _latest_ release is now fetched by default if not specified
  - Downloaded pipeline files are now properly executable.
- Fixed bugs in `nf-core list`
  - Sorting now works again
  - Output is partially coloured (better highlighting out of date pipelines)
  - Improved documentation
- Fixed bugs in `nf-core lint`
  - The order of conda channels is now correct, avoiding occasional erroneous errors that packages weren't found ([#207](https://github.com/nf-core/tools/issues/207))
  - Allow edge versions in nf-core pipelines
- Add reporting of ignored errored process
  - As a solution for [#103](https://github.com/nf-core/tools/issues/103))
- Add Bowtie2 and BWA in iGenome config file template

## [v1.5 - Iron Shark](https://github.com/nf-core/tools/releases/tag/1.5) - [2019-03-13]

### Template pipeline

- Dropped Singularity file
- Summary now logs details of the cluster profile used if from [nf-core/configs](https://github.com/nf-core/configs)
- Dockerhub is used in favor of Singularity Hub for pulling when using the Singularity profile
- Changed default container tag from latest to dev
- Brought the logo to life
- Change the default filenames for the pipeline trace files
- Remote fetch of nf-core/configs profiles fails gracefully if offline
- Remove `params.container` and just directly define `process.container` now
- Completion email now includes MultiQC report if not too big
- `params.genome` is now checked if set, to ensure that it's a valid iGenomes key
- Together with nf-core/configs, helper function now checks hostname and suggests a valid config profile
- `awsbatch` executor requires the `tracedir` not to be set to an `s3` bucket.

### Tools helper code

- New `nf-core launch` command to interactively launch nf-core pipelines from command-line
  - Works with a `parameters.settings.json` file shipped with each pipeline
  - Discovers additional `params` from the pipeline dynamically
- Drop Python 3.4 support
- `nf-core list` now only shows a value for _"is local latest version"_ column if there is a local copy.
- Lint markdown formatting in automated tests
  - Added `markdownlint-cli` for checking Markdown syntax in pipelines and tools repo
- Syncing now reads from a `blacklist.json` in order to exclude pipelines from being synced if necessary.
- Added nf-core tools API description to assist developers with the classes and functions available.
  - Docs are automatically built by Travis CI and updated on the nf-co.re website.
- Introduced test for filtering remote workflows by keyword.
- Build tools python API docs
  - Use Travis job for api doc generation and publish

- `nf-core bump-version` now stops before making changes if the linting fails
- Code test coverage
  - Introduced test for filtering remote workflows by keyword
- Linting updates
  - Now properly searches for conda packages in default channels
  - Now correctly validates version pinning for packages from PyPI
  - Updates for changes to `process.container` definition

### Other

- Bump `conda` to 4.6.7 in base nf-core Dockerfile

## [v1.4 - Tantalum Butterfly](https://github.com/nf-core/tools/releases/tag/1.4) - [2018-12-12]

### Template pipeline

- Institutional custom config profiles moved to github `nf-core/configs`
  - These will now be maintained centrally as opposed to being shipped with the pipelines in `conf/`
  - Load `base.config` by default for all profiles
  - Removed profiles named `standard` and `none`
  - Added parameter `--igenomesIgnore` so `igenomes.config` is not loaded if parameter clashes are observed
  - Added parameter `--custom_config_version` for custom config version control. Can use this parameter to provide commit id for reproducibility. Defaults to `master`
  - Deleted custom configs from template in `conf/` directory i.e. `uzh.config`, `binac.config` and `cfc.config`
- `multiqc_config` and `output_md` are now put into channels instead of using the files directly (see issue [#222](https://github.com/nf-core/tools/issues/222))
- Added `local.md` to cookiecutter template in `docs/configuration/`. This was referenced in `README.md` but not present.
- Major overhaul of docs to add/remove parameters, unify linking of files and added description for providing custom configs where necessary
- Travis: Pull the `dev` tagged docker image for testing
- Removed UPPMAX-specific documentation from the template.

### Tools helper code

- Make Travis CI tests fail on pull requests if the `CHANGELOG.md` file hasn't been updated
- Minor bugfixing in Python code (eg. removing unused import statements)
- Made the web requests caching work on multi-user installations
- Handle exception if nextflow isn't installed
- Linting: Update for Travis: Pull the `dev` tagged docker image for testing

## [v1.3 - Citreous Swordfish](https://github.com/nf-core/tools/releases/tag/1.3) - [2018-11-21]

- `nf-core create` command line interface updated
  - Interactive prompts for required arguments if not given
  - New flag for workflow author
- Updated channel order for bioconda/conda-forge channels in environment.yaml
- Increased code coverage for sub command `create` and `licenses`
- Fixed nasty dependency hell issue between `pytest` and `py` package in Python 3.4.x
- Introduced `.coveragerc` for pytest-cov configuration, which excludes the pipeline template now from being reported
- Fix [189](https://github.com/nf-core/tools/issues/189): Check for given conda and PyPi package dependencies, if their versions exist
- Added profiles for `cfc`,`binac`, `uzh` that can be synced across pipelines
  - Ordering alphabetically for profiles now
- Added `pip install --upgrade pip` to `.travis.yml` to update pip in the Travis CI environment

## [v1.2](https://github.com/nf-core/tools/releases/tag/1.2) - [2018-10-01]

- Updated the `nf-core release` command
  - Now called `nf-core bump-versions` instead
  - New flag `--nextflow` to change the required nextflow version instead
- Template updates
  - Simpler installation of the `nf-core` helper tool, now directly from PyPI
  - Bump minimum nextflow version to `0.32.0` - required for built in `manifest.nextflowVersion` check and access to `workflow.manifest` variables from within nextflow scripts
  - New `withName` syntax for configs
  - Travis tests fail if PRs come against the `master` branch, slightly refactored
  - Improved GitHub contributing instructions and pull request / issue templates
- New lint tests
  - `.travis.yml` test for PRs made against the `master` branch
  - Automatic `--release` option not used if the travis repo is `nf-core/tools`
  - Warnings if depreciated variables `params.version` and `params.nf_required_version` are found
- New `nf-core licences` subcommand to show licence for each conda package in a workflow
- `nf-core list` now has options for sorting pipeline nicely
- Latest version of conda used in nf-core base docker image
- Updated PyPI deployment to correctly parse the markdown readme (hopefully!)
- New GitHub contributing instructions and pull request template

## [v1.1](https://github.com/nf-core/tools/releases/tag/1.1) - [2018-08-14]

Very large release containing lots of work from the first nf-core hackathon, held in SciLifeLab Stockholm.

- The [Cookiecutter template](https://github.com/nf-core/cookiecutter) has been merged into tools
  - The old repo above has been archived
  - New pipelines are now created using the command `nf-core create`
  - The nf-core template and associated linting are now controlled under the same version system
- Large number of template updates and associated linting changes
  - New simplified cookiecutter variable usage
  - Refactored documentation - simplified and reduced duplication
  - Better `manifest` variables instead of `params` for pipeline name and version
  - New integrated nextflow version checking
  - Updated travis docker pull command to use tagging to allow release tests to pass
  - Reverted Docker and Singularity syntax to use `ENV` hack again
- Improved Python readme parsing for PyPI
- Updated Travis tests to check that the correct `dev` branch is being targeted
- New sync tool to automate pipeline updates
  - Once initial merges are complete, a nf-core bot account will create PRs for future template updates

## [v1.0.1](https://github.com/nf-core/tools/releases/tag/1.0.1) - [2018-07-18]

The version 1.0 of nf-core tools cannot be installed from PyPi. This patch fixes it, by getting rid of the requirements.txt plus declaring the dependent modules in the setup.py directly.

## [v1.0](https://github.com/nf-core/tools/releases/tag/1.0) - [2018-06-12]

Initial release of the nf-core helper tools package. Currently includes four subcommands:

- `nf-core list`: List nf-core pipelines with local info
- `nf-core download`: Download a pipeline and singularity container
- `nf-core lint`: Check pipeline against nf-core guidelines
- `nf-core release`: Update nf-core pipeline version number

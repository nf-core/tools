from pathlib import Path
from unittest import mock

import pytest
import requests_cache
import responses
import yaml

import nf_core.modules.create
from nf_core.components.create import ComponentCreate
from nf_core.modules.containers import ModuleContainers
from nf_core.modules.modules_utils import ContainerEntry
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS
from tests.utils import (
    mock_anaconda_api_calls,
    mock_biotools_api_calls,
)

from ..test_modules import TestModules


class TestModulesCreate(TestModules):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(ComponentCreate, "_build_seqera_containers")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_modules_create_succeed(self):
        """Succeed at creating the TrimGalore! module"""
        with responses.RequestsMock() as rsps:
            mock_anaconda_api_calls(rsps, "trim-galore", "0.6.7")
            module_create = nf_core.modules.create.ModuleCreate(
                self.pipeline_dir, "trimgalore", "@author", "process_single", True, True, conda_name="trim-galore"
            )
            with requests_cache.disabled():
                module_create.create()
        assert Path(self.pipeline_dir, "modules", "local", "trimgalore/main.nf").exists()

    def test_modules_create_fail_exists(self):
        """Fail at creating the same module twice"""
        with responses.RequestsMock() as rsps:
            mock_anaconda_api_calls(rsps, "trim-galore", "0.6.7")
            module_create = nf_core.modules.create.ModuleCreate(
                self.pipeline_dir, "trimgalore", "@author", "process_single", False, False, conda_name="trim-galore"
            )
            with requests_cache.disabled():
                module_create.create()
            with pytest.raises(UserWarning) as excinfo, requests_cache.disabled():
                module_create.create()
        assert "module directory exists:" in str(excinfo.value)

    def test_modules_create_nfcore_modules(self):
        """Create a module in nf-core/modules clone"""
        with responses.RequestsMock() as rsps:
            mock_anaconda_api_calls(rsps, "fastqc", "0.11.9")
            module_create = nf_core.modules.create.ModuleCreate(
                self.nfcore_modules, "fastqc", "@author", "process_low", False, False
            )
            with requests_cache.disabled():
                module_create.create()
        assert Path(self.nfcore_modules, "modules", "nf-core", "fastqc", "main.nf").exists()
        assert Path(self.nfcore_modules, "modules", "nf-core", "fastqc", "tests", "main.nf.test").exists()

    def test_modules_create_nfcore_modules_subtool(self):
        """Create a tool/subtool module in a nf-core/modules clone"""
        with responses.RequestsMock() as rsps:
            mock_anaconda_api_calls(rsps, "star", "2.8.10a")
            module_create = nf_core.modules.create.ModuleCreate(
                self.nfcore_modules, "star/index", "@author", "process_medium", False, False
            )
            with requests_cache.disabled():
                module_create.create()
        assert Path(self.nfcore_modules, "modules", "nf-core", "star", "index", "main.nf").exists()
        assert Path(self.nfcore_modules, "modules", "nf-core", "star", "index", "tests", "main.nf.test").exists()

    def test_modules_meta_yml_structure_biotools_meta(self):
        """Test the structure of the module meta.yml file when it was generated with INFORMATION from bio.tools and WITH a meta."""
        with responses.RequestsMock() as rsps:
            mock_anaconda_api_calls(rsps, "bpipe", "0.9.13--hdfd78af_0")
            mock_biotools_api_calls(rsps, "bpipe")
            module_create = nf_core.modules.create.ModuleCreate(
                self.nfcore_modules, "bpipe/test", "@author", "process_single", has_meta=True, force=True
            )
            module_create.create()

        expected_yml = {
            "name": "bpipe_test",
            "description": "write your description here",
            "keywords": ["sort", "example", "genomics"],
            "tools": [
                {
                    "bpipe": {
                        "description": "",
                        "homepage": "http://test",
                        "documentation": "http://test",
                        "tool_dev_url": "http://test",
                        "doi": "",
                        "licence": ["MIT"],
                        "identifier": "biotools:bpipe",
                    }
                }
            ],
            "input": [
                [
                    {
                        "meta": {
                            "type": "map",
                            "description": "Groovy Map containing sample information. e.g. `[ id:'sample1' ]`",
                        }
                    },
                    {
                        "raw_sequence": {
                            "type": "file",
                            "description": "raw_sequence file",
                            "pattern": "*.{fastq-like,sam}",
                            "ontologies": [
                                {"edam": "http://edamontology.org/data_0848"},
                                {"edam": "http://edamontology.org/format_2182"},
                                {"edam": "http://edamontology.org/format_2573"},
                            ],
                        }
                    },
                ]
            ],
            "output": {
                "sequence_report": [
                    [
                        {
                            "meta": {
                                "type": "map",
                                "description": "Groovy Map containing sample information. e.g. `[ id:'sample1' ]`",
                            }
                        },
                        {
                            "*.{html}": {
                                "type": "file",
                                "description": "sequence_report file",
                                "pattern": "*.{html}",
                                "ontologies": [
                                    {"edam": "http://edamontology.org/data_2955"},
                                    {"edam": "http://edamontology.org/format_2331"},
                                ],
                            }
                        },
                    ]
                ],
                "versions_bpipe": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"bpipe": {"type": "string", "description": "The name of the tool"}},
                        {
                            "bpipe --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "topics": {
                "versions": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"bpipe": {"type": "string", "description": "The name of the tool"}},
                        {
                            "bpipe --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "authors": ["@author"],
            "maintainers": ["@author"],
        }

        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)

        assert meta_yml == expected_yml

    def test_modules_meta_yml_structure_biotools_nometa(self):
        """Test the structure of the module meta.yml file when it was generated with INFORMATION from bio.tools and WITHOUT a meta."""
        with responses.RequestsMock() as rsps:
            mock_anaconda_api_calls(rsps, "bpipe", "0.9.13--hdfd78af_0")
            mock_biotools_api_calls(rsps, "bpipe")
            module_create = nf_core.modules.create.ModuleCreate(
                self.nfcore_modules, "bpipe/test", "@author", "process_single", has_meta=False, force=True
            )
            module_create.create()

        expected_yml = {
            "name": "bpipe_test",
            "description": "write your description here",
            "keywords": ["sort", "example", "genomics"],
            "tools": [
                {
                    "bpipe": {
                        "description": "",
                        "homepage": "http://test",
                        "documentation": "http://test",
                        "tool_dev_url": "http://test",
                        "doi": "",
                        "licence": ["MIT"],
                        "identifier": "biotools:bpipe",
                    }
                }
            ],
            "input": [
                {
                    "raw_sequence": {
                        "type": "file",
                        "description": "raw_sequence file",
                        "pattern": "*.{fastq-like,sam}",
                        "ontologies": [
                            {"edam": "http://edamontology.org/data_0848"},
                            {"edam": "http://edamontology.org/format_2182"},
                            {"edam": "http://edamontology.org/format_2573"},
                        ],
                    }
                }
            ],
            "output": {
                "sequence_report": [
                    {
                        "*.{html}": {
                            "type": "file",
                            "description": "sequence_report file",
                            "pattern": "*.{html}",
                            "ontologies": [
                                {"edam": "http://edamontology.org/data_2955"},
                                {"edam": "http://edamontology.org/format_2331"},
                            ],
                        }
                    }
                ],
                "versions_bpipe": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"bpipe": {"type": "string", "description": "The name of the tool"}},
                        {
                            "bpipe --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "topics": {
                "versions": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"bpipe": {"type": "string", "description": "The name of the tool"}},
                        {
                            "bpipe --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "authors": ["@author"],
            "maintainers": ["@author"],
        }

        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)

        assert meta_yml == expected_yml

    @mock.patch("nf_core.utils.anaconda_package")
    @mock.patch("nf_core.components.components_utils.get_biotools_response")
    @mock.patch("rich.prompt.Confirm.ask")
    def test_modules_meta_yml_structure_template_meta(
        self, mock_rich_ask, mock_biotools_response, mock_anaconda_package
    ):
        """Test the structure of the module meta.yml file when it was generated with TEMPLATE data and WITH a meta."""
        mock_biotools_response.return_value = {}
        mock_anaconda_package.return_value = {}
        mock_rich_ask.return_value = False  # Don't provide Bioconda package name
        module_create = nf_core.modules.create.ModuleCreate(
            self.nfcore_modules, "test", "@author", "process_single", has_meta=True, empty_template=False
        )
        module_create.create()

        expected_yml = {
            "name": "test",
            "description": "write your description here",
            "keywords": ["sort", "example", "genomics"],
            "tools": [
                {
                    "test": {
                        "description": "",
                        "homepage": "",
                        "documentation": "",
                        "tool_dev_url": "",
                        "doi": "",
                        "licence": None,
                        "identifier": None,
                    }
                }
            ],
            "input": [
                [
                    {
                        "meta": {
                            "type": "map",
                            "description": "Groovy Map containing sample information\ne.g. `[ id:'sample1' ]`\n",
                        }
                    },
                    {
                        "bam": {
                            "type": "file",
                            "description": "Sorted BAM/CRAM/SAM file",
                            "pattern": "*.{bam,cram,sam}",
                            "ontologies": [
                                {"edam": "http://edamontology.org/format_2572"},
                                {"edam": "http://edamontology.org/format_2573"},
                                {"edam": "http://edamontology.org/format_3462"},
                            ],
                        }
                    },
                ]
            ],
            "output": {
                "bam": [
                    [
                        {
                            "meta": {
                                "type": "map",
                                "description": "Groovy Map containing sample information\ne.g. `[ id:'sample1' ]`\n",
                            }
                        },
                        {
                            "*.bam": {
                                "type": "file",
                                "description": "Sorted BAM/CRAM/SAM file",
                                "pattern": "*.{bam,cram,sam}",
                                "ontologies": [
                                    {"edam": "http://edamontology.org/format_2572"},
                                    {"edam": "http://edamontology.org/format_2573"},
                                    {"edam": "http://edamontology.org/format_3462"},
                                ],
                            }
                        },
                    ]
                ],
                "versions_test": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"test": {"type": "string", "description": "The name of the tool"}},
                        {
                            "test --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "topics": {
                "versions": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"test": {"type": "string", "description": "The name of the tool"}},
                        {
                            "test --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "authors": ["@author"],
            "maintainers": ["@author"],
        }

        with open(Path(self.nfcore_modules, "modules", "nf-core", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)

        assert meta_yml == expected_yml

    @mock.patch("nf_core.utils.anaconda_package")
    @mock.patch("nf_core.components.components_utils.get_biotools_response")
    @mock.patch("rich.prompt.Confirm.ask")
    def test_modules_meta_yml_structure_template_nometa(
        self, mock_rich_ask, mock_biotools_response, mock_anaconda_package
    ):
        """Test the structure of the module meta.yml file when it was generated with TEMPLATE data and WITHOUT a meta."""
        mock_biotools_response.return_value = {}
        mock_anaconda_package.return_value = {}
        mock_rich_ask.return_value = False  # Don't provide Bioconda package name
        module_create = nf_core.modules.create.ModuleCreate(
            self.nfcore_modules, "test", "@author", "process_single", has_meta=False, empty_template=False
        )
        module_create.create()

        expected_yml = {
            "name": "test",
            "description": "write your description here",
            "keywords": ["sort", "example", "genomics"],
            "tools": [
                {
                    "test": {
                        "description": "",
                        "homepage": "",
                        "documentation": "",
                        "tool_dev_url": "",
                        "doi": "",
                        "licence": None,
                        "identifier": None,
                    }
                }
            ],
            "input": [
                {
                    "bam": {
                        "type": "file",
                        "description": "Sorted BAM/CRAM/SAM file",
                        "pattern": "*.{bam,cram,sam}",
                        "ontologies": [
                            {"edam": "http://edamontology.org/format_2572"},
                            {"edam": "http://edamontology.org/format_2573"},
                            {"edam": "http://edamontology.org/format_3462"},
                        ],
                    }
                }
            ],
            "output": {
                "bam": [
                    {
                        "*.bam": {
                            "type": "file",
                            "description": "Sorted BAM/CRAM/SAM file",
                            "pattern": "*.{bam,cram,sam}",
                            "ontologies": [
                                {"edam": "http://edamontology.org/format_2572"},
                                {"edam": "http://edamontology.org/format_2573"},
                                {"edam": "http://edamontology.org/format_3462"},
                            ],
                        }
                    }
                ],
                "versions_test": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"test": {"type": "string", "description": "The name of the tool"}},
                        {
                            "test --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "topics": {
                "versions": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"test": {"type": "string", "description": "The name of the tool"}},
                        {
                            "test --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "authors": ["@author"],
            "maintainers": ["@author"],
        }

        with open(Path(self.nfcore_modules, "modules", "nf-core", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)

        assert meta_yml == expected_yml

    @mock.patch("nf_core.utils.anaconda_package")
    @mock.patch("nf_core.components.components_utils.get_biotools_response")
    @mock.patch("rich.prompt.Confirm.ask")
    def test_modules_meta_yml_structure_empty_meta(self, mock_rich_ask, mock_biotools_response, mock_anaconda_package):
        """Test the structure of the module meta.yml file when it was generated with an EMPTY template and WITH a meta."""
        mock_biotools_response.return_value = {}
        mock_anaconda_package.return_value = {}
        mock_rich_ask.return_value = False  # Don't provide Bioconda package name
        module_create = nf_core.modules.create.ModuleCreate(
            self.nfcore_modules, "test", "@author", "process_single", has_meta=True, empty_template=True
        )
        module_create.create()

        expected_yml = {
            "name": "test",
            "description": "write your description here",
            "keywords": ["sort", "example", "genomics"],
            "tools": [
                {
                    "test": {
                        "description": "",
                        "homepage": "",
                        "documentation": "",
                        "tool_dev_url": "",
                        "doi": "",
                        "licence": None,
                        "identifier": None,
                    }
                }
            ],
            "input": [
                [
                    {
                        "meta": {
                            "type": "map",
                            "description": "Groovy Map containing sample information. e.g. `[ id:'sample1' ]`",
                        }
                    },
                    {"input": {"type": "file", "description": "", "pattern": "", "ontologies": [{"edam": ""}]}},
                ]
            ],
            "output": {
                "output": [
                    [
                        {
                            "meta": {
                                "type": "map",
                                "description": "Groovy Map containing sample information. e.g. `[ id:'sample1' ]`",
                            }
                        },
                        {"*": {"type": "file", "description": "", "pattern": "", "ontologies": [{"edam": ""}]}},
                    ]
                ],
                "versions_test": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"test": {"type": "string", "description": "The name of the tool"}},
                        {
                            "test --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "topics": {
                "versions": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"test": {"type": "string", "description": "The name of the tool"}},
                        {
                            "test --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "authors": ["@author"],
            "maintainers": ["@author"],
        }

        with open(Path(self.nfcore_modules, "modules", "nf-core", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)

        assert meta_yml == expected_yml

    @mock.patch("nf_core.utils.anaconda_package")
    @mock.patch("nf_core.components.components_utils.get_biotools_response")
    @mock.patch("rich.prompt.Confirm.ask")
    def test_modules_meta_yml_structure_empty_nometa(
        self, mock_rich_ask, mock_biotools_response, mock_anaconda_package
    ):
        """Test the structure of the module meta.yml file when it was generated with an EMPTY template and WITHOUT a meta."""
        mock_biotools_response.return_value = {}
        mock_anaconda_package.return_value = {}
        mock_rich_ask.return_value = False  # Don't provide Bioconda package name
        module_create = nf_core.modules.create.ModuleCreate(
            self.nfcore_modules, "test", "@author", "process_single", has_meta=False, empty_template=True
        )
        module_create.create()

        expected_yml = {
            "name": "test",
            "description": "write your description here",
            "keywords": ["sort", "example", "genomics"],
            "tools": [
                {
                    "test": {
                        "description": "",
                        "homepage": "",
                        "documentation": "",
                        "tool_dev_url": "",
                        "doi": "",
                        "licence": None,
                        "identifier": None,
                    }
                }
            ],
            "input": [{"input": {"type": "file", "description": "", "pattern": "", "ontologies": [{"edam": ""}]}}],
            "output": {
                "output": [{"*": {"type": "file", "description": "", "pattern": "", "ontologies": [{"edam": ""}]}}],
                "versions_test": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"test": {"type": "string", "description": "The name of the tool"}},
                        {
                            "test --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "topics": {
                "versions": [
                    [
                        {"${task.process}": {"type": "string", "description": "The name of the process"}},
                        {"test": {"type": "string", "description": "The name of the tool"}},
                        {
                            "test --version": {
                                "type": "eval",
                                "description": "The expression to obtain the version of the tool",
                            }
                        },
                    ]
                ],
            },
            "authors": ["@author"],
            "maintainers": ["@author"],
        }

        with open(Path(self.nfcore_modules, "modules", "nf-core", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)

        assert meta_yml == expected_yml


class TestModulesCreateSeqeraContainers(TestModules):
    """`modules create` builds Seqera/Wave containers for the new module instead of using BioContainers."""

    @mock.patch.object(ModuleContainers, "get_conda_lock_file")
    @mock.patch.object(ModuleContainers, "request_container")
    def test_create_builds_seqera_containers(self, mock_request_container, mock_get_conda_lock_file):
        """Creating a module wires the Wave-built containers into main.nf.

        The Wave HTTP layer (``request_container`` / ``get_conda_lock_file``) is mocked so
        the real container building – exercised in ``tests/modules/test_containers.py`` – is
        not re-tested here; this only asserts the build is invoked and its result lands in
        ``main.nf``.
        """
        docker_image = "community.wave.seqera.io/library/fastqc:0.11.9--docker"
        singularity_https = "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/ab/abc/data"

        def fake_request_container(cs, platform, environment_yml, verbose=False, on_build_id=None, cancel_event=None):
            if cs == "singularity":
                return ContainerEntry(name=f"sif-{platform}", build_id=f"bd-sing-{platform}", https=singularity_https)
            return ContainerEntry(name=docker_image, build_id=f"bd-docker-{platform}", scan_id="sc")

        mock_request_container.side_effect = fake_request_container
        mock_get_conda_lock_file.return_value = "# conda lock file content"

        with responses.RequestsMock() as rsps:
            mock_anaconda_api_calls(rsps, "fastqc", "0.11.9")
            module_create = nf_core.modules.create.ModuleCreate(
                self.nfcore_modules, "fastqc", "@author", "process_low", False, False
            )
            with requests_cache.disabled():
                module_create.create()

        main_nf = Path(self.nfcore_modules, "modules", "nf-core", "fastqc", "main.nf").read_text()
        assert docker_image in main_nf
        assert singularity_https in main_nf
        assert "YOUR-TOOL-HERE" not in main_nf

        # Wave was asked to build every container system / platform combination
        assert mock_request_container.call_count == len(CONTAINER_SYSTEMS) * len(CONTAINER_PLATFORMS)

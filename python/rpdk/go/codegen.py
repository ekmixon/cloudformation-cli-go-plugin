
# pylint: disable=useless-super-delegation,too-many-locals
# pylint doesn't recognize abstract methods
import logging
import shutil

from rpdk.core.data_loaders import resource_stream
from rpdk.core.exceptions import InternalError, SysExitRecommendedError
from rpdk.core.init import input_with_validation
from rpdk.core.jsonutils.resolver import resolve_models
from rpdk.core.plugin_base import LanguagePlugin

from .resolver import translate_type
from .utils import safe_reserved, validate_path
from pathlib import Path

LOG = logging.getLogger(__name__)

OPERATIONS = ("Create", "Read", "Update", "Delete", "List")
EXECUTABLE = "cfn-cli"


class GoLanguagePlugin(LanguagePlugin):
    MODULE_NAME = __name__
    RUNTIME = "go1.x"
    ENTRY_POINT = "handler"
    TEST_ENTRY_POINT = "{}.HandlerWrapper::testEntrypoint"
    CODE_URI = "bin/"

    def __init__(self):
        self.env = self._setup_jinja_env(
            trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True
        )
        self.env.filters["translate_type"] = translate_type
        self.env.filters["safe_reserved"] = safe_reserved
        self.namespace = None

    def _prompt_for_go_path(self, project):
        namespace = project.root

        if ('github.com' in namespace.parts) :
            projectpath = namespace.parents[namespace.parts.index('github.com')- 2]
            namepath = namespace.relative_to(projectpath)
            prompt = "Enter the GO Import path (empty for default '{}'): ".format(str(namespace.relative_to(projectpath)))

        else :
            prompt = "Enter the GO Import path"


        self.import_path = input_with_validation(prompt, validate_path(namepath))
        project.settings["importpath"] = str(self.import_path )

    def init(self, project):
        LOG.debug("Init started")

        self._prompt_for_go_path(project)

        self._init_settings(project)

        # .gitignore
        path = project.root / ".gitignore"
        LOG.debug("Writing .gitignore: %s", path)
        contents = resource_stream(__name__, "data/go.gitignore").read()
        project.safewrite(path, contents)

        # project folder structure
        src = (project.root / "cmd"  / "resource")
        LOG.debug("Making source folder structure: %s", src)
        src.mkdir(parents=True, exist_ok=True)

        inter = (project.root / "internal")
        inter.mkdir(parents=True, exist_ok=True)


        # Makefile
        path = project.root / "Makefile"
        LOG.debug("Writing Makefile: %s", path)
        template = self.env.get_template("Makefile")
        contents = template.render()
        project.safewrite(path, contents)

        # CloudFormation/SAM template for handler lambda
        path = project.root / "template.yml"
        LOG.debug("Writing SAM template: %s", path)
        template = self.env.get_template("template.yml")

        handler_params = {
            "Handler": project.entrypoint,
            "Runtime": project.runtime,
            "CodeUri": self.CODE_URI,
        }
        contents = template.render(
            resource_type=project.type_name,
            functions={
                "TypeFunction": handler_params,
                "TestEntrypoint": {
                    **handler_params,
                    "Handler": handler_params["Handler"].replace(
                        "handleRequest", "testEntrypoint"
                    ),
                },
            },
        )
        project.safewrite(path, contents)

        LOG.debug("Writing handlers and tests")
        self.init_handlers(project, src)

        # README
        path = project.root / "README.md"
        LOG.debug("Writing README: %s", path)
        template = self.env.get_template("README.md")
        contents = template.render(
            type_name=project.type_name,
            schema_path=project.schema_path,
            executable=EXECUTABLE,
            files="generated.go and main.go"
        )
        project.safewrite(path, contents)

        LOG.debug("Init complete")

    def _init_settings(self, project):
        project.runtime = self.RUNTIME
        project.entrypoint = self.ENTRY_POINT.format(self.import_path)
        project.test_entrypoint = self.TEST_ENTRY_POINT.format(self.import_path)

    def init_handlers(self, project, src):
        LOG.debug("Writing stub handlers")
        template = self.env.get_template("StubHandler.go.tple")
        path = src / "Handlers.go"
        contents = template.render()
        project.safewrite(path, contents)


    def _get_generated_root(self, project):
        LOG.debug("Init started")


    def generate(self, project):
        LOG.debug("Generate started")
        root = project.root / "cmd"

         # project folder structure
        src = (root  / "resource")

        LOG.debug("Writing Types")
        models = resolve_models(project.schema)
        template = self.env.get_template("types.go.tple")
        path = src / "{}.go".format("Generated")
        contents = template.render(
            models=models,
            )
        project.overwrite(path, contents)

        path = root  / "main.go"
        LOG.debug("Writing project: %s", path)
        template = self.env.get_template("main.go.tple")
        importpath = Path(project.settings["importpath"])
        contents = template.render(
            path=importpath / 'cmd' / 'resource'
        )
        project.overwrite(path, contents)


        LOG.debug("Generate complete")

    def package(self, project):
        LOG.debug("Generate started")

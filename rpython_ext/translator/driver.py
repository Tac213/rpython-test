# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Optional, Self, Dict, Any
    from rpython.config.config import Config
    from rpython.translator.c.database import LowLevelDatabase
    from rpython_ext.translator.goal.translate import TargetSpecDict, CPythonModuleDef

from rpython.annotator.policy import AnnotatorPolicy
from rpython.jit.codewriter.policy import JitPolicy
from rpython.translator.driver import TranslationDriver, TranslationContext, taskdef, shutil_copy
from rpython_ext.translator.c.cpyext_tool import CPythonExtensionBuilder


class CPythonExtensionTranslationDriver(TranslationDriver):

    def __init__(
        self,
        setopts=None,
        default_goal=None,
        disable=None,
        extmod_name=None,
        config=None,
        overrides=None,
    ):
        # type: (Dict[str, Any], Optional[str], Optional[list[str]], Optional[str], Optional[Config], Dict[str, Any]) -> None
        if disable is None:
            disable = []
        super(CPythonExtensionTranslationDriver, self).__init__(
            setopts,
            default_goal,
            disable,
            None,
            extmod_name,
            config,
            overrides,
        )
        self.ext_module_def = {}  # type: CPythonModuleDef
        self.target_spec_dict = {}  # type: TargetSpecDict
        self.extra = {}  # type: TargetSpecDict
        self.policy = None  # type: Optional[AnnotatorPolicy]
        self.translator = TranslationContext(config=self.config)
        self.cbuilder = None  # type: Optional[CPythonExtensionBuilder]
        self.database = None  # type: Optional[LowLevelDatabase]

    def setup(self, ext_module_def, target_spec_dict, policy=None, empty_translator=None):
        # type: (CPythonModuleDef, TargetSpecDict, Optional[AnnotatorPolicy], Optional[TranslationContext]) -> None
        self.standalone = False
        self.ext_module_def = ext_module_def
        self.target_spec_dict = target_spec_dict
        self.extra = target_spec_dict

        if policy is None:
            policy = AnnotatorPolicy()
        self.policy = policy

        if empty_translator:
            self.translator = empty_translator
        self.translator.driver_instrument_result = self.instrument_result

    @classmethod
    def from_targetspec(
        cls,
        target_spec_dict,
        config=None,
        args=None,
        empty_translator=None,
        disable=None,
        default_goal=None,
    ):
        # type: (TargetSpecDict, Optional[Config], Optional[list[str]], Optional[TranslationContext], Optional[list[str]], Optional[str]) -> Self
        if args is None:
            args = []

        driver = cls(config=config, default_goal=default_goal, disable=disable)
        target = target_spec_dict["target"]
        driver.timer.start_event("loading target")
        spec = target(driver, args)
        if isinstance(spec, tuple):
            ext_module_def, policy = spec
        else:
            ext_module_def = spec
            policy = None
        driver.timer.end_event("loading target")

        driver.setup(ext_module_def, target_spec_dict, policy=policy, empty_translator=empty_translator)
        return driver

    @taskdef([], "Annotating&simplifying")
    def task_annotate(self):
        """
        Annotate
        """
        # includes annotation and annotatation simplifications
        translator = self.translator
        policy = self.policy
        self.log.info("with policy: {}.{}".format(policy.__class__.__module__, policy.__class__.__name__))

        annotator = translator.buildannotator(policy=policy)

        for func, input_types in self.ext_module_def.values():
            annotator.build_types(func, input_types, False)

        if "jit_entry_point" in self.target_spec_dict:
            jit_entry_point = self.target_spec_dict["jit_entry_point"]
            translator.entry_point_graph = annotator.bookkeeper.getdesc(self.ext_module_def[jit_entry_point][0]).getuniquegraph()

        self.sanity_check_annotation()
        annotator.complete()
        annotator.simplify()

    @taskdef(
        [
            TranslationDriver.STACKCHECKINSERTION,
            "?" + TranslationDriver.BACKENDOPT,
            TranslationDriver.RTYPE,
            "?annotate",
        ],
        "Creating database for generating c source",
        earlycheck=TranslationDriver.possibly_check_for_boehm,
    )
    def task_database_c(self):
        """
        Create a database for further backend generation
        """
        translator = self.translator
        if translator.annotator is not None:
            translator.frozen = True

        get_gchooks = self.target_spec_dict.get("get_gchooks", lambda: None)
        gchooks = get_gchooks()

        cbuilder = CPythonExtensionBuilder(
            self.translator,
            self.config,
            self.ext_module_def,
            gchooks=gchooks,
            name=self.extmod_name,
        )
        cbuilder.modulename = self.extmod_name
        database = cbuilder.build_database()
        self.log.info("database for generating C source was created")
        self.cbuilder = cbuilder
        self.database = database

    @taskdef(["compile_c"], "Copy the compiled shared libary into CPython's site-packages directory.")
    def task_create_extension(self):
        # type: () -> None
        """
        Copy the compiled shared libary into CPython's site-packages directory.
        """
        assert self.cbuilder is not None
        extension_path = self.cbuilder.get_entry_point()
        targetext = self.cbuilder.site_packages_dir.join(extension_path.basename)
        shutil_copy(str(extension_path), str(targetext))
        self.log.info("created: {}".format(targetext))

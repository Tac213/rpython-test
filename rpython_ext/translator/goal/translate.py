# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
import sys
import os
import optparse
try:
    from importlib import machinery, util
except ImportError:
    machinery = None
    util = None
try:
    import imp  # type: ignore
except ImportError:
    imp = None
try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import TypedDict, Callable, Union, TypeVar, ParamSpec
    from rpython.annotator.policy import AnnotatorPolicy
    from rpython.jit.codewriter.policy import JitPolicy
    from rpython.memory.gc.hook import GcHooks

from rpython.config.config import (
    to_optparse,
    OptionDescription,
    Config,
    BoolOption,
    IntOption,
    StrOption,
    ChoiceOption,
    ArbitraryOption,
    OptHelpFormatter,
)
from rpython.config.translationoption import (
    get_combined_translation_config,
    set_platform,
    set_opt_level,
    OPT_LEVELS,
    DEFAULT_OPT_LEVEL,
)
from rpython.translator.goal.translate import (
    GOALS,
    log,
    goal_options,
    show_help,
    log_config,
)
from rpython.translator.driver import TranslationContext
from rpython_ext.translator.driver import CPythonExtensionTranslationDriver



CPYEXT_TRANSLATE_OPTION_DESCR = OptionDescription(
    "translate",
    "Translate rpython program to cpython extension.",
    [
        StrOption(
            "targetspec",
            "Target spec of thhe rpython program.",
            default='targetcpythonext',
            cmdline=None,
        ),
        ChoiceOption(
            "opt",
            "optimization level",
            OPT_LEVELS,
            default=DEFAULT_OPT_LEVEL,
            cmdline="--opt -O",
        ),
        BoolOption(
            "debug",
            "Debug the translate process using debugpy.",
            default=False,
            cmdline="--debug",
        ),
        BoolOption(
            "profile",
            "cProfile (to debug the speed of the translation process)",
            default=False,
            cmdline="--profile",
        ),
        BoolOption(
            "batch",
            "Don't run interactive helpers",
            default=False,
            cmdline="--batch",
            negation=False,
        ),
        IntOption(
            "huge",
            "Threshold in the number of functions after which "
            "a local call graph and not a full one is displayed",
            default=100,
            cmdline="--huge",
        ),
        BoolOption(
            "view",
            "Start the pygame viewer",
            default=False,
            cmdline="--view",
            negation=False,
        ),
        BoolOption(
            "help",
            "show this help message and exit",
            default=False,
            cmdline="-h --help",
            negation=False,
        ),
        BoolOption(
            "fullhelp",
            "show full help message and exit",
            default=False,
            cmdline="--full-help",
            negation=False,
        ),
        # xxx default goals ['annotate', 'rtype', 'backendopt', 'source', 'compile']
        ArbitraryOption(
            "goals",
            "XXX",
            defaultfactory=list,
        ),
        ArbitraryOption(
            "skipped_goals",
            "XXX",
            defaultfactory=list,
        ),
        OptionDescription(
            "goal_options",
            "Goals that should be reached during translation",
            goal_options(),
        ),
    ]
)


def load_cpyext_target(target_spec):
    # type: (str) -> TargetSpecDict
    log.info("Translating target as defined by {}".format(target_spec))
    if not target_spec.endswith(".py"):
        target_spec += ".py"
    thismod = sys.modules[__name__]
    sys.modules["translate"] = thismod
    spec_name = os.path.splitext(os.path.basename(target_spec))[0]
    dir_name = os.path.dirname(target_spec)
    if machinery and util:
        loader = machinery.SourceFileLoader(spec_name, target_spec)
        spec = util.spec_from_file_location(spec_name, target_spec, loader=loader)
        assert spec, "Failed to load module spec for target spec: {}".format(target_spec)
        mod = util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    elif imp:
        fp, pathname, description = imp.find_module(spec_name, [dir_name])
        try:
            mod = imp.load_module(spec_name, fp, pathname, description)
        finally:
            if fp:
                fp.close()
    else:
        log.WARNING(
            "Neither 'importlib' nor 'imp' could be imported, "
            "trying to modify sys.path to load the targe spec."
        )
        sys.path.insert(0, dir_name)
        mod = __import__(spec_name)
        sys.path.remove(dir_name)
    if "target" not in mod.__dict__:
        raise KeyError("File {} is not a valid cpython extension target.".format(target_spec))
    return mod.__dict__


def parse_cpyext_options_and_load_target():
    # type: () -> tuple[TargetSpecDict, Config, Config, list[str]]
    opt_parser = optparse.OptionParser(
        usage="%prog [options] [target] [target-specific-options]",
        formatter=OptHelpFormatter(),
        add_help_option=False,
        prog="translate",
    )
    opt_parser.disable_interspersed_args()

    # Add target-specific-options and cpyext-translate-option
    # to the `opt_parser`.
    config = get_combined_translation_config(translating=True)
    to_optparse(config, parser=opt_parser, useoptions=['translation.*'])
    translateconfig = Config(CPYEXT_TRANSLATE_OPTION_DESCR)
    to_optparse(translateconfig, parser=opt_parser)

    # Parse command line arguments.
    options, args = opt_parser.parse_args()

    # set goals and skipped_goals
    reset = False
    for name, _, _, _ in GOALS:
        if name.startswith('?'):
            continue
        if getattr(translateconfig.goal_options, name):
            if name not in translateconfig.goals:
                translateconfig.goals.append(name)
        if getattr(translateconfig.goal_options, 'no_' + name):
            if name not in translateconfig.skipped_goals:
                if not reset:
                    translateconfig.skipped_goals[:] = []
                    reset = True
                translateconfig.skipped_goals.append(name)

    if args:
        target_spec = os.path.normpath(args[0])
        args = args[1:]
        if os.path.isfile("{}.py".format(target_spec)):
            assert not os.path.isfile(target_spec), "Ambiguous file naming, please rename {}".format(target_spec)
            translateconfig.targetspec = target_spec
        elif os.path.isfile(target_spec) and target_spec.endswith(".py"):
            translateconfig.targetspec = os.path.splitext(target_spec)[0]
        else:
            log.ERROR("Could not find target {}".format(target_spec))
            sys.exit(1)
    else:
        show_help(translateconfig, opt_parser, None, config)

    # print the version of the host
    # (if it's PyPy, it includes the hg checksum)
    log.info(sys.version)

    # apply the platform settings
    set_platform(config)

    target_spec = translateconfig.targetspec
    target_spec_dict = load_cpyext_target(target_spec)

    if args and not target_spec_dict.get("task_options", False):
        log.WARNING("Target specific arguments supplied but will be ignored: {}".format(" ".join(args)))

    # give the target the possibility to get its own configuration options
    # into the config
    if "get_additional_config_options" in target_spec_dict:
        optiondescr = target_spec_dict["get_additional_config_options"]()
        config = get_combined_translation_config(
            optiondescr,
            existing_config=config,
            translating=True,
        )

    config.translation.rpython_translate = True

    # show the target-specific help if --help was given
    show_help(translateconfig, opt_parser, target_spec_dict, config)

    # apply the optimization level settings
    set_opt_level(config, translateconfig.opt)

    # let the target modify or prepare itself
    # based on the config
    if "handle_config" in target_spec_dict:
        target_spec_dict["handle_config"](config, translateconfig)

    return target_spec_dict, translateconfig, config, args


def cpython_extension_main():
    # type: () -> None
    sys.setrecursionlimit(2000)  # PyPy can't translate within cpython's 1k limit
    target_spec_dict, translateconfig, config, args = parse_cpyext_options_and_load_target()

    if translateconfig.debug:
        import debugpy
        debugpy.listen(("localhost", 8142))
        log.info("Waiting for a debugging client to attach on the process, localhost:8142")
        debugpy.wait_for_client()

    if translateconfig.opt == "jit":
        assert "jit_entry_point" in target_spec_dict, "You need to define the 'jit_entry_point' if you want to translate your CPython extension with a JIT compiler."
    if translateconfig.profile:
        from cProfile import Profile
        prof = Profile()
        prof.enable()
    else:
        prof = None

    translation_context = TranslationContext(config=config)

    def finish_profiling():
        # type: () -> None
        if prof:
            prof.disable()
            statfilename = "prof.dump"
            log.info("Dumping profiler stats to: {}".format(statfilename))
            prof.dump_stats(statfilename)

    try:
        driver = CPythonExtensionTranslationDriver.from_targetspec(
            target_spec_dict,
            config,
            args,
            empty_translator=translation_context,
            disable=translateconfig.skipped_goals,
            default_goal="create_extension",
        )
        log_config(translateconfig, "translate.py configuration")
        if config.translation.jit:
            if (translateconfig.goals != ['annotate'] and translateconfig.goals != ['rtype']):
                driver.set_extra_goals(['pyjitpl'])
            # early check:
            from rpython.jit.backend.detect_cpu import getcpuclassname
            getcpuclassname(config.translation.jit_backend)

        log_config(config.translation, "translation configuration")

        if config.translation.output:
            driver.extmod_name = config.translation.output
        elif driver.extmod_name is None and "__name__" in target_spec_dict:
            driver.extmod_name = target_spec_dict["__name__"]

        goals = translateconfig.goals
        try:
            driver.proceed(goals)
        finally:
            driver.timer.pprint()
    finally:
        finish_profiling()


if TYPE_CHECKING:
    BaseAnnotation = Union[type[bool], type[int], type[float], type[str], None, type]
    Annotation = Union[BaseAnnotation, list["Annotation"], tuple["Annotation", ...]]
    _P = ParamSpec("_P")
    _T = TypeVar("_T")
    CPythonFunctionDef = tuple[Callable[_P, _T], list[Annotation]]
    CPythonModuleDef = dict[str, CPythonFunctionDef]
    TargetSpecDict = TypedDict(
        "TargetSpecDcit",
        {
            "__name__": str,
            "target": Callable[[CPythonExtensionTranslationDriver, list[str]], Union[CPythonModuleDef, tuple[CPythonModuleDef, AnnotatorPolicy]]],
            "take_options": bool,
            "get_additional_config_options": Callable[[], OptionDescription],
            "handle_config": Callable[[Config, Config], None],
            "jitpolicy": Callable[[CPythonExtensionTranslationDriver], JitPolicy],
            "get_gchooks": Callable[[], GcHooks],
            "get_llinterp_args": Callable[[], list],
            "jit_entry_point": str,
        },
        total=False,
    )


if __name__ == "__main__":
    cpython_extension_main()

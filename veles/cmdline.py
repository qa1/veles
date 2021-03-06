# -*- coding: utf-8 -*-
"""
.. invisible:
     _   _ _____ _     _____ _____
    | | | |  ___| |   |  ___/  ___|
    | | | | |__ | |   | |__ \ `--.
    | | | |  __|| |   |  __| `--. \
    \ \_/ / |___| |___| |___/\__/ /
     \___/\____/\_____|____/\____/

Created on Jul 2, 2014

Base class for __main__'s Main class and others which are topmost script
classes.

███████████████████████████████████████████████████████████████████████████████

Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.

███████████████████████████████████████████████████████████████████████████████
"""


try:
    import argcomplete
except:
    pass
from argparse import RawDescriptionHelpFormatter, ArgumentParser, \
    ArgumentError, _StoreConstAction
from email.utils import formatdate
import logging
import sys

import veles
from veles.compat import from_none, has_colors


class classproperty(object):
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class CommandLineArgumentsRegistry(type):
    """
    Metaclass to accumulate command line options from scattered classes for
    velescli's upmost argparse.
    """
    classes = []

    def __init__(cls, name, bases, clsdict):
        super(CommandLineArgumentsRegistry, cls).__init__(name, bases, clsdict)
        cls.argv = property(lambda _: CommandLineBase.argv)
        # if the class does not have it's own init_parser(), no-op
        init_parser = clsdict.get('init_parser', None)
        if init_parser is None:
            return
        # early check for the method existence
        if not isinstance(init_parser, staticmethod):
            raise TypeError("init_parser must be a static method since the "
                            "class has CommandLineArgumentsRegistry metaclass")
        CommandLineArgumentsRegistry.classes.append(cls)

    @property
    def class_argv(cls):
        return CommandLineBase.argv


class CommandLineBase(object):
    """
    Start point of any VELES engine executions.
    """

    LOGO_PLAIN = veles.__logo__

    LOGO_COLORED = "\033" r"[1;32m _   _ _____ _     _____ _____  " \
                   "\033[0m\n" \
                   "\033" r"[1;32m| | | |  ___| |   |  ___/  ___| " \
                   "\033[0m" + \
                   (" Version \033[1;36m%s\033[0m" % veles.__version__) + \
                   (" %s\n" % formatdate(veles.__date__, True)) + \
                   "\033" r"[1;32m| | | | |__ | |   | |__ \ `--.  " \
                   "\033[0m\033[0;37m %s\033[0m\n" % veles.__logo_ext__[0] + \
                   "\033" r"[1;32m| | | |  __|| |   |  __| `--. \ " "\033[0m" \
                   "\033[0;37m %s" % veles.__logo_ext__[1] + \
                   "\033[0m\n" \
                   "\033" r"[1;32m\ \_/ / |___| |___| |___/\__/ / " "\033[0m" \
                   "\033[0;37m %s" % veles.__logo_ext__[2] + \
                   "\033[0m\n" \
                   "\033" r"[1;32m \___/\____/\_____|____/\____/  " "\033[0m" \
                   "\033[0;37m %s\033[0m\n" % veles.__logo_ext__[3]

    LOGO = LOGO_COLORED if has_colors() else LOGO_PLAIN
    DRY_RUN_CHOICES = ["load", "init", "exec", "no"]
    LOG_LEVEL_MAP = {"debug": logging.DEBUG, "info": logging.INFO,
                     "warning": logging.WARNING, "error": logging.ERROR}
    SPECIAL_OPTS = ["--help", "--html-help", "--version", "--frontend",
                    "--dump-config"]
    _argv = tuple()

    class SortingRawDescriptionHelpFormatter(RawDescriptionHelpFormatter):
        def add_arguments(self, actions):
            actions = sorted(actions, key=lambda x: x.dest)
            super(CommandLineBase.SortingRawDescriptionHelpFormatter,
                  self).add_arguments(actions)

    @staticmethod
    def init_parser(sphinx=False, ignore_conflicts=False):
        """
        Creates the command line argument parser.
        """

        parser = ArgumentParser(
            description=CommandLineBase.LOGO if not sphinx else "",
            formatter_class=CommandLineBase.SortingRawDescriptionHelpFormatter)
        for cls in CommandLineArgumentsRegistry.classes:
            try:
                parser = cls.init_parser(parser=parser)
            except ArgumentError as e:
                if not ignore_conflicts:
                    raise from_none(e)
        parser.add_argument("--no-logo", default=False,
                            help="Do not print VELES version, copyright and "
                                 "other information on startup.",
                            action='store_true')
        parser.add_argument("--version", action="store_true",
                            help="Print version number, date, commit hash and "
                                 "exit.")
        parser.add_argument("--html-help", action="store_true",
                            help="Open VELES help in your web browser.")
        parser.add_argument(
            "--frontend", action="store_true",
            help="Open VELES command line frontend in the default web browser "
                 "and run the composed line.")
        parser.add_argument("-v", "--verbosity", type=str, default="info",
                            choices=CommandLineBase.LOG_LEVEL_MAP.keys(),
                            help="Set the logging verbosity level.")
        parser.add_argument("--debug", type=str, default="",
                            help="Set DEBUG logging level for these classes "
                                 "(separated by comma)")
        parser.add_argument("--debug-pickle", default=False,
                            help="Turn on pickle diagnostics.",
                            action='store_true')
        parser.add_argument("-r", "--random-seed", type=str,
                            default="/dev/urandom:16",
                            help="Set the random generator seed, e.g. "
                                 "veles/samples/seed:1024,:1024 or "
                                 "/dev/urandom:16:uint32 or "
                                 "hex string with even number of digits")
        parser.add_argument('-w', '--snapshot', default="",
                            help='workflow snapshot')
        parser.add_argument("--dump-config", default=False,
                            help="Print the initial global configuration",
                            action='store_true')
        parser.add_argument("--dry-run", default="no",
                            choices=CommandLineBase.DRY_RUN_CHOICES,
                            help="no: normal work; load: stop before loading/"
                                 "creating the workflow; init: stop before "
                                 "workflow initialization; exec: stop before "
                                 "workflow execution.")
        parser.add_argument("--visualize", default=False,
                            help="initialize, but do not run the loaded "
                                 "model, show workflow graph and plots",
                            action='store_true')
        parser.add_argument(
            "--optimize",
            help="Perform optimization of the model's parameters using the "
                 "genetic algorithm. Format: <size>[:<generations>], where "
                 "<size> is the number of species in the population (if not "
                 "sure, set it to 50) and <generations> is the optional limit "
                 "of evaluated generations. If <generations> is not set, "
                 "the optimization will continue until there is no fitness "
                 "improvement.")
        parser.add_argument(
            "--ensemble-train",
            help="Parameters to assemble the ensemble of trained models. "
                 "Format is <size>:<ratio>, where size is the number of models"
                 " to train and ratio is the part of the training set to use "
                 "during the training for each model (picked randomly). The "
                 "models' evaluation results will be written to --result-file."
                 " They include achieved metric values and outputs on the test"
                 " dataset (loader must support test mode).")
        parser.add_argument(
            "--ensemble-test",
            help="Test the trained ensemble (see --ensemble-train). The value "
                 "of this argument must be a path to --result-file with the "
                 "ensemble_train definition. --test is ignored.")
        parser.add_argument("--workflow-graph", default="",
                            help="Save workflow graph to file.")
        parser.add_argument("--dump-unit-attributes", default="no",
                            help="Print unit __dict__-s after workflow "
                                 "initialization, excluding large numpy arrays"
                                 " if \"pretty\" is chosen.",
                            choices=['no', 'pretty', 'all'])
        parser.add_argument(
            'workflow', help='Path to Python script with the VELES model.'
        ).pretty_name = "workflow file"
        parser.add_argument(
            'config', help="Path to the configuration file "
                           "(pass \"-\" to make it <workflow>_config.py, "
                           "pass empty to ignore)."
        ).pretty_name = "configuration file"
        arg = parser.add_argument(
            'config_list',
            help="Configuration overrides separated by a whitespace, for "
                 "example: \nroot.global_alpha=0.006\n "
                 "root.snapshot_prefix='test_pr'", nargs='*',
            metavar="key=value")
        arg.pretty_name = "override configuration"
        arg.important = True
        parser.add_argument("-b", "--background", default=False,
                            help="Run in background as a daemon.",
                            action='store_true')
        try:
            class NoEscapeCompleter(argcomplete.CompletionFinder):
                def quote_completions(self, completions, *args, **kwargs):
                    return completions

            NoEscapeCompleter()(parser)  # pylint: disable=E1102
        except:
            pass
        return parser

    @staticmethod
    def map_parser_keyword_arguments():
        parser = CommandLineBase.init_parser()
        return {action.dest: action for action in parser._actions}

    @classproperty
    def argv(cls):
        if cls._argv is None:
            cls.setup_argv()
        return cls._argv

    @staticmethod
    def setup_argv(sys_argv=True, reset_argv=False, *args, **kwargs):
        argv = list(CommandLineBase._argv)
        args = list(args)
        if reset_argv:
            del argv[:]
        if len(argv) == 0:
            if sys_argv:
                argv.extend(sys.argv[1:])
            if len(kwargs) > 0:
                available = CommandLineBase.map_parser_keyword_arguments()
                if not set(kwargs).issubset(set(available)):
                    raise ValueError(
                        "The following keyword arguments are not supported: "
                        "%s" % ",".join(set(kwargs) - set(available)))
                for key, val in kwargs.items():
                    action = available[key]
                    if len(action.option_strings) > 0:
                        argv.append(action.option_strings[-1])
                        if not isinstance(action, _StoreConstAction):
                            argv.append(str(val))
                    else:
                        args.append(str(val))
            argv.extend(args)
        if not sys_argv:
            assert len(args) >= 2
        CommandLineBase._argv = tuple(argv)

#!/usr/bin/env python
"""
Runs test files
"""

from __future__ import print_function
from collections import namedtuple
import io
import os.path
import subprocess
import sys
import yaml
import csv
import argparse
import tempfile
import json


def main():
    parser = argparse.ArgumentParser(description="Tests CDE calculations in YAML.")
    parser.add_argument("registry_yaml", metavar="YAML", nargs=1,
                        type=argparse.FileType("r"),
                        help="File containing YAML definition of registry")
    parser.add_argument("test_csvs", metavar="CSV", nargs="+",
                        type=argparse.FileType("r"),
                        help="CSV files containing test definitions")
    parser.add_argument("--outfile", metavar="FILE", type=argparse.FileType("w"),
                        help="Output file")
    parser.add_argument("--verbose", "-v", action="count",
                        help="More info for debugging tests")

    args = parser.parse_args()

    if not args.outfile:
        args.outfile = sys.stdout

    registry = load_yaml(args.registry_yaml[0])

    success = True
    for infile in args.test_csvs:
        success = run_tests(registry, infile, args) and success
    return 0 if success else 1


Registry = namedtuple("Registry", ("names", "calculations"))


def load_yaml(file_obj):
    calculations = {}
    names = {}
    data = yaml.load(file_obj)
    for cde in data.get("cdes") or []:
        if cde.get("code"):
            calc = cde.get("calculation")
            if calc:
                calculations[cde["code"]] = calc
        names[cde["code"]] = cde.get("name")
    return Registry(names, calculations)


TestResult = namedtuple("TestResult", ("test", "expected", "actual", "error", "output"))
TestCase = namedtuple("TestCase", ("file", "number", "check_code", "params", "desc"))


def run_tests(registry, csv_file, opts):
    num_tests = 0
    num_success = 0
    num_errors = 0
    for index, row in enumerate(csv.DictReader(csv_file)):
        num_tests += 1
        t = setup_test(row, index + 1, csv_file.name)
        res = run_test(registry, t)

        if res.error:
            print_error(registry, res, t.params, opts)
            num_errors += 1
        elif res.expected == res.actual:
            print_success(registry, res, t.params, opts)
            num_success += 1
        else:
            print_failure(registry, res, t.params, opts)

    return num_tests == num_success


def setup_test(cols, num, filename):
    params = {code: val for code, val in cols.items()
              if code not in ("check", "testcase")}
    desc = cols.get("testcase", "")
    return TestCase(filename, num, cols["check"], params, desc)


def load_adsafe_js():
    adsafe_path = "../rdrf/rdrf/static/js/vendor/adsafe-min.js"
    return io.open(os.path.join(os.path.dirname(__file__), adsafe_path)).read()


def run_test(registry, test):
    context = {code: val for code, val in test.params.items()
               if code in registry.names}
    patient = {code: val for code, val in test.params.items()
               if code not in registry.names}
    script = registry.calculations[test.check_code]

    script = u"""
        "use strict";
        var document = {};
        var window = { console: console };
        %s

        var patient = %s;
        var context = %s;
        var RDRF = ADSAFE;

        %s

        console.log(context.result);
    """ % (load_adsafe_js(), json.dumps(patient), json.dumps(context), script)

    success, output = exec_script(script)

    if success:
        context_result, output = parse_output(output)
        return TestResult(test, test.params[test.check_code].strip(), context_result,
                          False, output)
    else:
        return TestResult(test, None, None, True, output)


def parse_output(output):
    lines = [o.strip() for o in output.split("\n")]
    non_empty = filter(bool, lines)
    result = non_empty[-1] if non_empty else None
    return (result, "\n".join(lines[0:-1]) + "\n")


def exec_script(script):
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".js", prefix="registry_test_") as js:
        js.write(script)
        js.flush()

        try:
            p = subprocess.Popen(["node", js.name],
                                 stdin=None, close_fds=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            output, _ = p.communicate()
            output = output.decode("utf-8", errors="replace")
            if p.returncode != 0:
                return False, output
            return True, output
        except OSError as e:
            return False, "Couldn't execute %s: %s" % (script, e)
    return False, "Test bug"


def print_success(registry, result, params, opts):
    if opts.verbose > 1:
        log(opts, u"PASS: %s:%s %s\n" % (result.test.file, result.test.number, result.test.desc))


def print_error(registry, result, params, opts):
    log(opts, u"ERROR: %s\n" % str(result.output))


def print_failure(registry, result, params, opts):
    log(opts,
        u"FAIL %s:%s: %s (%s) was \"%s\", expected \"%s\".\n" % (result.test.file,
                                                                 result.test.number,
                                                                 result.test.check_code,
                                                                 registry.names[result.test.check_code],
                                                                 result.actual,
                                                                 result.expected))
    if opts.verbose:
        for param in sorted(params):
            if param in registry.names:
                log(opts, u"    %s (%s) = \"%s\"\n" %
                    (param, registry.names[param], params[param]))
            else:
                log(opts, u"    Patient %s = \"%s\"\n" % (param, params[param]))
        if result.output:
            log(opts, result.output)


def log(opts, text):
    opts.outfile.write(text)


if __name__ == '__main__':
    sys.exit(main())

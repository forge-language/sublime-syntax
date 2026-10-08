#!/usr/bin/env python3
"""Run standalone Forge syntax/archive checks in a disposable portable profile.

Requires a pre-provisioned official Linux Sublime distribution and Xvfb. No
application download or global profile is changed. This runner has no language
server or editor helper package dependency.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
def require(condition, message):
    if not condition:
        raise AssertionError(message)

import json
import os
import re
import sys
import traceback
import sublime
RESULT = os.environ['FORGE_SUBLIME_RESULT']
state = {'build': sublime.version(), 'python_optimization': sys.flags.optimize, 'errors': [], 'syntax_assertions': 0}
view = None
attempt = 0

def finish(error=None):
    if error:
        state['errors'].append(str(error))
    with open(RESULT, 'w') as stream:
        json.dump(state, stream, indent=2)

def check_syntax():
    global view
    try:
        syntax = next((item for item in sublime.find_syntax_by_scope('source.forge') if item.path == 'Packages/Forge/Forge.sublime-syntax'), None)
        require(syntax and syntax.scope == 'source.forge', 'Archive syntax unavailable')
        fixture = os.environ['FORGE_SUBLIME_FIXTURE']
        text = open(fixture).read()
        view = sublime.active_window().new_file()
        view.run_command('append', {'characters': text})
        view.assign_syntax(syntax)
        source_row = None
        for row, line in enumerate(text.splitlines()):
            assertion = re.match('//\\s*(<-|\\^+)\\s+(.+)$', line)
            if not assertion:
                source_row = row
                continue
            marker, selector = assertion.groups()
            column = 0 if marker == '<-' else line.index('^')
            for offset in range(1 if marker == '<-' else len(marker)):
                point = view.text_point(source_row, column + offset)
                require(view.match_selector(point, selector), 'Fixture line {} column {}: {} does not match {}'.format(source_row + 1, column + offset + 1, view.scope_name(point), selector))
                state['syntax_assertions'] += 1
        require(state['syntax_assertions'], 'No syntax assertions executed')
        require(sublime.find_syntax_for_file('example.fg').scope == 'source.forge', 'Extension detection failed')
        state['archive_syntax'] = True
        editor = sublime.active_window().new_file()
        editor.assign_syntax(syntax)
        require(editor.settings().get('tab_size') == 2, 'Forge indentation setting missing')
        editor.run_command('append', {'characters': 'native main {\nprintln("{");\n// {\nreturn 0;\n}\n'})
        editor.run_command('reindent', {'single_line': False})
        formatted = editor.substr(sublime.Region(0, editor.size())).splitlines()
        require(formatted == ['native main {', '  println("{");', '  // {', '  return 0;', '}'], 'Actual indentation rules failed: ' + repr(formatted))
        editor.sel().clear()
        editor.sel().add(sublime.Region(0, 0))
        editor.run_command('toggle_comment', {'block': False})
        require(editor.substr(sublime.Region(0, editor.size())).startswith('// '), 'Comment toggle missing')
        editor.run_command('toggle_comment', {'block': False})
        require(editor.substr(sublime.Region(0, editor.size())).startswith('native main'), 'Comment untoggle failed')
        state['editor_indentation_and_comments'] = True
        finish()
    except Exception:
        finish(traceback.format_exc())


def plugin_loaded():
    sublime.set_timeout(check_syntax, 3000)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sublime', type=Path, required=True, help='Official Linux sublime_text executable')
    parser.add_argument('--archive', type=Path, default=ROOT / 'dist/Forge.sublime-package')
    parser.add_argument('--fixture', type=Path, default=ROOT / 'tests/syntax_test_forge.fg', help='Syntax fixture for positive or negative editor validation')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--result', type=Path, help='Write JSON evidence after deleting the temporary profile')
    parser.add_argument('--save-profile', type=Path, help='Explicitly preserve this disposable profile for offline integration tests')
    args = parser.parse_args()
    executable = args.sublime.resolve()
    if not executable.is_file() or not args.archive.is_file():
        parser.error('Sublime executable and built archive must exist')
    if not args.fixture.is_file():
        parser.error('Syntax fixture must exist')
    with tempfile.TemporaryDirectory(prefix='forge-sublime-smoke-') as temporary:
        root = Path(temporary)
        distribution = root / 'sublime'
        shutil.copytree(executable.parent, distribution, ignore=shutil.ignore_patterns('Data'))
        data = distribution / 'Data'
        packages = data / 'Packages'
        installed = data / 'Installed Packages'
        installed.mkdir(parents=True, exist_ok=True)
        user = packages / 'User'
        user.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.archive, installed / 'Forge.sublime-package')
        (user / 'Preferences.sublime-settings').write_text(json.dumps({'hot_exit': False, 'remember_open_files': False, 'ignored_packages': ['Vintage']}))
        harness = packages / 'ForgeIntegrationTests'
        harness.mkdir(parents=True, exist_ok=True)
        (harness / '.python-version').write_text('3.8')
        (harness / 'integration.py').write_text(HARNESS)
        fixture = harness / 'syntax_test_forge.fg'
        if args.fixture:
            shutil.copy2(args.fixture, fixture)
        source = root / 'main.fg'
        source.write_text('native main {\n    println("hello");\n}\n')
        result = root / 'result.json'
        env = dict(os.environ, FORGE_SUBLIME_RESULT=str(result), FORGE_SUBLIME_FIXTURE=str(fixture) if args.fixture else '',
            FORGE_SUBLIME_SOURCE=str(source))
        log = root / 'sublime.log'
        for phase in range(1):
            with log.open('a') as output:
                process = subprocess.Popen(['xvfb-run', '-a', str(distribution / executable.name), '--multiinstance', '-n'], env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    deadline = time.monotonic() + args.timeout
                    while not result.exists() and time.monotonic() < deadline:
                        if process.poll() is not None:
                            break
                        time.sleep(.2)
                    if not result.exists():
                        raise RuntimeError('Sublime smoke timed out or exited:\n' + log.read_text()[-16000:])
                    evidence = json.loads(result.read_text())
                    if args.result:
                        args.result.write_text(json.dumps(evidence, indent=2) + '\n')
                    print(json.dumps(evidence, indent=2))
                    if args.save_profile:
                        shutil.copytree(data, args.save_profile, dirs_exist_ok=True)
                        args.save_profile.chmod(0o700)
                    if evidence['errors']:
                        raise RuntimeError('Real-editor check failed:\n' + log.read_text()[-16000:])
                finally:
                    import signal
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()



if __name__ == '__main__':
    main()

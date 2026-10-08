"""Contracts for the independent Forge syntax package (stdlib only)."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import plistlib
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('forge_package', ROOT / 'scripts/build-package.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageTests(unittest.TestCase):
    def resource(self, name):
        return json.loads((ROOT / name).read_text())

    def test_archive_is_deterministic_and_syntax_only(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            for name in builder.FILES:
                target = fixture / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            (fixture / 'plugin.py').write_text('raise RuntimeError()')
            with patch.object(builder, 'ROOT', fixture), contextlib.redirect_stdout(io.StringIO()):
                target = builder.build()
                first = target.read_bytes()
                builder.build()
                self.assertEqual(first, target.read_bytes())
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.namelist(), sorted(builder.FILES))
                self.assertFalse(any(name.endswith('.py') or 'LSP' in name for name in archive.namelist()))
                for entry in archive.infolist():
                    self.assertEqual(entry.date_time, (2026, 1, 1, 0, 0, 0))
                    self.assertEqual(entry.external_attr >> 16, 0o100644)
            self.assertEqual(target.with_name(target.name + '.sha256').read_text(),
                             hashlib.sha256(first).hexdigest() + '  Forge.sublime-package\n')

    def test_missing_and_symlink_assets_preserve_existing_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            (fixture / 'dist').mkdir()
            target = fixture / 'dist/Forge.sublime-package'
            target.write_bytes(b'previous valid release')
            source = fixture / 'resource'
            with patch.object(builder, 'ROOT', fixture), patch.object(builder, 'FILES', ('resource',)):
                with self.assertRaises(ValueError):
                    builder.build()
                real = fixture / 'real'
                real.write_text('resource')
                source.symlink_to(real)
                with self.assertRaises(ValueError):
                    builder.build()
            self.assertEqual(target.read_bytes(), b'previous valid release')
            self.assertFalse(target.with_suffix('.tmp').exists())

    def test_independent_package_control_metadata(self):
        package = self.resource('packages.json')['packages'][0]
        self.assertEqual(package['name'], 'Forge')
        self.assertEqual(package['details'], 'https://github.com/forge-language/sublime-syntax')
        self.assertEqual(package['releases'], [{'sublime_text': '>=4132', 'tags': True}])
        self.assertNotIn('dependencies', package)

    def test_build_commands_use_argv_and_project_directory(self):
        build = self.resource('Forge.sublime-build')
        self.assertEqual(build['selector'], 'source.forge')
        self.assertEqual(build['cmd'], ['forge', 'build'])
        self.assertEqual(build['working_dir'], '${project_path:${folder:$file_path}}')
        variants = {variant['name']: variant for variant in build['variants']}
        self.assertEqual(variants['Check File']['cmd'], ['forge', '$file', '--check'])
        self.assertEqual(variants['Check File']['working_dir'], '$file_path')
        self.assertEqual(variants['Run Project']['cmd'], ['forge', 'run'])
        for command in [build, *build['variants']]:
            self.assertNotIn('shell_cmd', command)
            self.assertNotIn('shell', command)

    def test_actual_comment_and_indentation_preferences(self):
        with (ROOT / 'Comments.tmPreferences').open('rb') as source:
            preferences = plistlib.load(source)
        self.assertEqual(preferences['scope'], 'source.forge')
        settings = preferences['settings']
        self.assertEqual(settings['shellVariables'], [{'name': 'TM_COMMENT_START', 'value': '// '}])
        increase = re.compile(settings['increaseIndentPattern'])
        for line in ['native main {', 'if (ready) { // closing brace }', 'fn name(): int {']:
            self.assertIsNotNone(increase.search(line), line)
        for line in ['// {', 'println("{");', 'native main {}']:
            self.assertIsNone(increase.search(line), line)
        self.assertRegex('  }', settings['decreaseIndentPattern'])
        defaults = self.resource('Forge.sublime-settings')
        self.assertEqual(defaults['tab_size'], 2)
        self.assertTrue(defaults['translate_tabs_to_spaces'])
        self.assertTrue(defaults['auto_indent'])
        self.assertTrue(defaults['smart_indent'])
        self.assertNotIn('increase_indent_pattern', defaults)
        self.assertNotIn('decrease_indent_pattern', defaults)

    def test_snippets_and_syntax_fixture_use_forge_package(self):
        triggers = set()
        for source in (ROOT / 'snippets').glob('*.sublime-snippet'):
            snippet = ET.parse(source).getroot()
            self.assertEqual(snippet.findtext('scope'), 'source.forge')
            self.assertTrue(snippet.findtext('content').strip())
            triggers.add(snippet.findtext('tabTrigger'))
        self.assertEqual(triggers, {'ffor', 'ffn', 'fimport', 'fmain'})
        header = (ROOT / 'tests/syntax_test_forge.fg').read_text().splitlines()[0]
        self.assertIn('Packages/Forge/Forge.sublime-syntax', header)
        self.assertNotIn('LSP-Forge', header)

    def test_settings_menu_targets_independent_package(self):
        commands = self.resource('Default.sublime-commands')
        self.assertEqual(commands[0]['command'], 'edit_settings')
        self.assertEqual(commands[0]['args']['base_file'], '${packages}/Forge/Forge.sublime-settings')
        menu = (ROOT / 'Main.sublime-menu').read_text()
        self.assertIn('${packages}/Forge/Forge.sublime-settings', menu)
        self.assertNotIn('LSP-Forge', menu)


if __name__ == '__main__':
    unittest.main()

# Forge for Sublime Text

The **Forge** package adds `.fg` syntax highlighting, two-space indentation,
`//` comment toggling, snippets and build commands to Sublime Text 4 (build 4132
or newer). It works without a language server or Python editor plugin.

This repository is [forge-language/sublime-syntax](https://github.com/forge-language/sublime-syntax).
The optional **LSP-Forge** package in
[forge-language/sublime-text](https://github.com/forge-language/sublime-text)
provides language-server integration separately. Install both when you want
editor diagnostics and language features.

## Install

Until default-channel acceptance, run **Package Control: Add Repository** with
`https://raw.githubusercontent.com/forge-language/sublime-syntax/main/packages.json`,
then **Package Control: Install Package → Forge**. Tagged releases provide updates.

Alternatively, download `Forge.sublime-package` and its SHA-256 file from
[GitHub Releases](https://github.com/forge-language/sublime-syntax/releases/latest).
Verify the checksum and copy the archive into
**Installed Packages**, next to the directory opened by **Preferences → Browse
Packages**. For a source installation, copy this repository into **Packages/Forge**.

Open a `.fg` file. Sublime selects **Forge** automatically. You can select it
manually from **View → Syntax → Forge**. No Forge compiler is needed for syntax
highlighting, comments, indentation or snippets.

**Preferences → Package Settings → Forge → Syntax Settings** opens user
preferences. The command palette also provides **Preferences: Forge Syntax Settings**.

## Build, check and run

Install the [Forge SDK](https://github.com/forge-language/forge) and make `forge`
available on the PATH inherited by Sublime Text. The compiler requires a host C
compiler for native builds. Choose **Tools → Build System → Forge**.

| Action | Command | Working directory |
| --- | --- | --- |
| Build | `forge build` | Project-file directory, first opened folder, or current-file directory |
| Check File | `forge <current-file> --check` | Current-file directory |
| Run Project | `forge run` | Same directory as Build |

Build and Run Project expect `forge.json` in that directory. **Tools → Build
With…** selects a variant. Check File invokes the compiler's parse-only check;
it does not establish complete type or ownership safety. The build definition
uses executable-and-argument arrays, without a shell. To customize paths or
commands, place a `build_systems` entry in your Sublime project.

## Highlighting and snippets

The grammar follows Forge's current lexer: `//` line comments, double-quoted
strings including multiline strings and escapes, decimal integers and floats,
keywords, types and operators. It does not introduce block comments,
hexadecimal literals, exponent notation or single-quoted strings. Highlighting
provides lexical scopes; it does not validate program semantics.

Type a trigger and press Tab:

| Trigger | Expansion |
| --- | --- |
| `fmain` | Native entry point |
| `ffn` | Function |
| `ffor` | Counted loop |
| `fimport` | Module import |

## Development

Use Python 3 to run the archive checks and build a reproducible package:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build-package.py
```

The output is `dist/Forge.sublime-package` and its SHA-256 file. Only the
allowlisted syntax resources, snippets, menus, README and license enter the
archive. Build scripts and tests remain outside it.

For Sublime's own syntax tests, install the source as **Packages/Forge**, open
`tests/syntax_test_forge.fg` and select **Tools → Build System → Syntax Tests**.
The fixture uses `Packages/Forge/Forge.sublime-syntax` explicitly.

Apache License 2.0; see [LICENSE](LICENSE).

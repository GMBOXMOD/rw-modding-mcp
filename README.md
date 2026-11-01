English | [简体中文](README.zh-CN.md)

# Rusted Warfare Modding MCP

[![M8ven Score](https://m8ven.ai/badge/mcp/gmboxmod-rw-modding-mcp-193cu7?v=6d952b5c688774a21da25c611d40cb66)](https://m8ven.ai/mcp/gmboxmod-rw-modding-mcp-193cu7?s=readme)

An MCP server for Rusted Warfare mod development. Five read-only tools.

Repository: `https://github.com/GMBOXMOD/rw-modding-mcp` · Changes: [CHANGELOG.md](CHANGELOG.md)

## Tools

| Tool | What it does |
|---|---|
| `lookup_key` | Look up a key by section. Returns a short definition plus examples by default, preserving sources, cross-source conflicts, and constraints. Full material on request. |
| `search_source` | Batch-search the Java source with bounded context, pagination, empty-result diagnostics, and a content budget. |
| `get_ref` | Look up events, functions, enums, memory types, and rules by topic and name. No arguments returns the full quick-reference tables. |
| `lint` | Static check on a file or directory. Accepts batch `paths`; unchanged files reuse the previous verdict. |
| `explain_actions` | Draws the call graph from events / autoTrigger / buttons → actions → `alsoTriggerAction`, flagging repeat, conditions, and memory reads/writes. |

All tools are read-only. None of them modify your files.

Query many keys with `lookup_key(keys=[...])`, check many files with `lint(paths=[...])`.
Batch queries cut model round-trips and trimmed output cuts what enters the context; actual cost depends on the client, the model, and caching.
The local lint cache only saves checking time — it is not the model's prompt cache. The MCP also cannot cap the client's Bash, sub-agent, or model request budget.

## Companion Skill

`skill/` holds the companion development-guide skill, for clients that support Skills (Claude Code, CodeBuddy, and others):

| File | Contents |
|---|---|
| `skill/SKILL.md` | Division of labour, workflow, hard-fact checklist, lint rule-number reference |
| `skill/references/铁锈战争模组开发Agent指南.md` | Full development guide (9 chapters + appendices) |
| `skill/references/反编译发现_运行时语义.md` | Implementation-level facts obtained by decompilation |
| `skill/references/反编译_字段对照表.md` | Obfuscated field → luke key mapping |
| `skill/references/锁步联机与动态帧率补偿.md` | Multiplayer / lockstep / frame-rate specifics |

The split is deliberate: **this MCP owns facts** (what a key is called, whether it exists, whether the code is valid),
**the skill owns judgement** (whether you should write it that way, why something fails silently, which tricks are outdated).

The skill ships **no scripts and no data tables** — both would duplicate this repository, and two copies of the truth drift apart.
For static checks use the `lint` tool; for a load test use `tools/game_loadtest.py`.

Install: copy the whole `skill/` directory into your client's skills directory and rename it to `rusted-warfare-modding`.

## Targeted Queries and Return Budget

The snippets below are MCP tool arguments, not shell commands:

```python
lookup_key(keys=["isVisible", "isActive", "displayType"], section="action")
lookup_key(key="isVisible", section="action", detail="full")
get_ref(topic="events", name="killedAnyUnit")
get_ref(topic="enums", name="movementType")
get_ref(topic="rules", name="alwaysSinglePress")
search_source(patterns=["setUnitStats", "setUnitMemory"], path_filter="custom/")
search_source(pattern="EventSourceReference|teamId", mode="regex")
```

- `lookup_key` defaults to `detail="brief"`: at most one short definition/example per section, at most three sections shown.
  Long descriptions are marked `truncated`; over-long examples are marked `example_omitted` rather than returned as half a config; sections not shown are marked `entries_omitted`.
  Constraints, source conflicts, and important notes are always kept.
  `section` accepts `action`, `[action_btn]`, or a chapter letter such as `M`.
  `section_match=false` means the material does not confirm usage in that section — it does not mean the key is unusable in the engine.
  Up to 32 distinct keys per call; repeated inputs are looked up once. `count` is the deduplicated number, `requested_count` is what you sent.
- **Return shape change**: the default mode no longer returns the raw `csv` / `cn` arrays but uses `entries`. Programs that depend on the
  raw fields should pass `detail="full"` explicitly. The old positional arguments are kept, and full mode keeps the original raw fields.
- `search_source` defaults to `10` matches with `2` lines of context on each side (`context_lines` accepts `0–5`).
  `patterns` takes up to 8 distinct queries per call; a line matching several terms is returned once, with counts in `by_pattern`.
  `mode="literal"` matches raw text — to find `%{` pass `%{` directly, not `%\{`.
  Use `mode="regex"` for regular expressions; the older `regex=True` still works but must not conflict with `mode="literal"`.
  `path_filter` is a path substring, not a glob. On empty results read `reason` / `hints` — it will not silently switch modes or widen the scope.
- Search `max_chars` defaults to `8000`, range `1000–20000`. It limits the compact-JSON character count of `matches`,
  **excludes result metadata, and is not a token count**. When the count or character budget is hit, pass `next_offset` as the next `offset`.
  Over-long matching lines or context are marked as truncated; pagination is stable only while the in-process source index is unchanged — after re-decompiling, restart the server.
- `get_ref()` with no arguments still returns the full quick-reference tables. Common topics: `events`, `functions`, `enums`, `memory`,
  `sections`, `rules`, `must_pair`, `hard_constraints`. `name` filters by name and requires `topic` alongside it.
  This round only queries existing material; no new tutorial templates were added, and "the name is listed" is not treated as verified runtime semantics.

For an ordinary unit, query narrowly first, then write the file and check it. Whether to spin up sub-agents or keep digging through source is a decision the client should put to the user separately, with a budget.

## Install

Python 3.10+ required.

```bash
git clone https://github.com/GMBOXMOD/rw-modding-mcp.git
cd rw-modding-mcp
python bootstrap.py --check     # see what the environment is missing
```

The first start creates a venv and installs `mcp` automatically — roughly 20–60 seconds.

## Client Configuration

```json
{
  "mcpServers": {
    "rusted-warfare": {
      "command": "python",
      "args": ["D:/path/to/rw-modding-mcp/bootstrap.py"]
    }
  }
}
```

For Claude Desktop write this into `claude_desktop_config.json`; for Cursor, `~/.cursor/mcp.json`; for Cline, `cline_mcp_settings.json`. VS Code's `.vscode/mcp.json` uses `servers` as the outer key — the contents are the same.

No `cwd` needed. `command` can be `python` or an absolute path.

Startup takes about 2.4 seconds; the client must keep the process alive for the duration of the session. To shave more time, skip the launcher:

```json
{
  "mcpServers": {
    "rusted-warfare": {
      "command": "D:/path/to/rw-modding-mcp/.venv/Scripts/python.exe",
      "args": ["D:/path/to/rw-modding-mcp/tools/rw_mcp_server.py"]
    }
  }
}
```

Run `python bootstrap.py --setup` once first. On Linux/macOS, replace `Scripts/python.exe` with `bin/python`.

## explain_actions

```bash
python tools/rw_explain.py "path/to/unit.ini"
python tools/rw_explain.py "path/to/unit.ini" --action scanThreatSlot   # single chain only
python tools/rw_explain.py "path/to/unit.ini" --json
```

The MCP returns the text graph by default; pass `fmt="json"` for the full structure.

It reports these six:

| Rule | What it checks |
|---|---|
| `loop-counter` | Whether the loop variable is reset to a constant before `repeat` on the same trigger chain, and whether the loop body advances it |
| `unreachable` | The action is defined but has no inbound edge and no trigger — it will never be called |
| `uninit-memory` | `@memory` is read but never written in this file (both `setUnitMemory` and `updateUnitMemory` count as writes) |
| `index-bound` | Loop index step > 1 (skipping cells) or carrying an offset (possible out-of-bounds) |
| `trailing-comment` | A `#` comment at end of line — the engine does not strip it, so the value is parsed with the comment attached |
| `unresolved-edge` | The action referenced by `alsoTriggerAction` does not exist |

It does not check runtime condition truth values, runtime `repeat`, cross-file edges introduced by `copyFrom`, or real array lengths. These are listed at the end of the output.

`lint`'s reference checks are isolated per unit and its local inheritance chain, and support relative `copyFrom`, `ROOT:`, basic `CORE:`, and the nearest
`all-units.template`. Missing or unexpandable inheritance (e.g. the vanilla directory cannot be located, or a dynamic path) is listed under `skipped` and must not be treated as verified.
This inheritance support applies to `lint` only; `explain_actions` still analyses a single file.

## CORE: Base Support

`copyFrom: CORE:tanks/tank.ini` reads the vanilla config from the game's `assets/units/tanks/tank.ini`,
not from `mods/units`. It only collects definitions — sections, constants — along the inheritance chain for reference checking. It does not modify or copy vanilla files, and does not launch the game.

Resolution order: the CLI's `--core-units` argument, the `RW_CORE_UNITS` environment variable, the directory of the given game-lib.jar
(`--jar` / `RW_GAME_JAR`), the game directory of the file being checked, then common install locations.
If an explicit `--core-units` / `RW_CORE_UNITS` path is invalid, it will not silently fall back to a different copy of the game.

```powershell
.venv/Scripts/python.exe tools/rw_lint.py "D:/path/to/mod" --core-units "D:/path/to/game/assets/units"
# For an MCP client, set RW_CORE_UNITS in the server environment, then restart the server.
```

- When the vanilla directory cannot be found, it is marked unresolved; when the directory is located but the target is missing, unreadable, or out of bounds, it reports `E17`.
- `core` in the CLI JSON and MCP results lists the vanilla directory and the referenced / read / unresolved counts.
- **`core.mode="symbols_only"` does not mean full unit validation passed**: it does not compute the final merged and overridden key values, and does not evaluate runtime expressions.
  What remains unchecked is listed in `core.not_checked`. `CORE:` and `SHARED:` resource paths inside images and audio are also outside this round's scope.
- Changing the relevant vanilla files or directory configuration invalidates the cache for checks that depend on them, without recomputing unrelated units.

## Command Line

Usable without installing the MCP:

```bash
python tools/rw_lint.py "D:/path/to/yourmod"            # static check (incremental by default)
python tools/rw_lint.py "D:/path/to/yourmod" --timing   # timings and cache hits
python tools/rw_lint.py "D:/path/to/yourmod" --no-cache # force a full run
python tools/rw_lint.py --ref                           # quick reference
python tools/rw_lint.py --json                          # machine-readable
python tools/rw_mcp/selftest.py                         # self-test
python tools/game_loadtest.py "D:/path/to/yourmod"      # in-game load test (headless)
```

## Optional Test Dependencies and External Mods

Validating the workflow YAML requires `PyYAML` in the Python environment running the tests, for example:

```powershell
.venv/Scripts/python.exe -m pip install PyYAML
.venv/Scripts/python.exe tests/run_tests.py
```

The real sample `example_test` is looked up in `RW_TEST_MOD_ROOTS`, then inside the repository, then beside it.
For other locations, set multiple parent directories via the environment variable (semicolon on Windows, colon on Linux/macOS):

```powershell
$env:RW_TEST_MOD_ROOTS = "D:/path/to/collection;D:/path/to/game/mods/units"
.venv/Scripts/python.exe tests/run_tests.py
.venv/Scripts/python.exe tools/rw_mcp/selftest.py
```

These tests only read mods and verify that results agree before and after caching, across the CLI and the MCP. They do not mean a mod has zero diagnostics, and they do not mean the game loads it.
Inheritance that stays unexpanded under `skipped` still needs separate handling; nothing here copies a mod or launches the game.

## search_source Needs Decompilation

```bash
python bootstrap.py --decompile
```

Requires JDK 17+. It finds the game directory automatically (or pass `--game`). Without this step, `search_source` returns nothing.

## Data Files

Three files under `references/`; without them `lookup_key` finds nothing:

- `官方代码表（Modding References）.csv`
- `单位代码表Modding API Reference.txt`
- `二进制键名.txt`

To use your own copies: `RW_CSV` / `RW_CN` (MCP only — the `lint` CLI does not read them).

## FAQ

**Startup fails** — check `bootstrap.log` in the repository root.

**Dependency install fails** — usually the network. Switch mirrors:

```bash
.venv/Scripts/python -m pip install -i https://mirrors.aliyun.com/pypi/simple mcp
```

**lint is clean but the unit won't shoot** — it only covers syntax and references. Whether the logic is right is for you to test.

**`lookup_key` says something wrong** — the tables are maintained by third parties. The `agreement` field in the response says whether both tables have the entry or only one; which one to trust is your call.

**Cache** — in `%LOCALAPPDATA%\rw-modding-mcp\lint` (on Linux/macOS it follows `~/.cache`). Disable with `--no-cache` or `RW_LINT_CACHE=0`.

## License

MIT, see `LICENSE`. The key-name material under `references/` is copyright of its respective authors; if you are an author and object to its inclusion, open an issue and it will be removed.

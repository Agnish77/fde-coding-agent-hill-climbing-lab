"""Coding agent with file discovery, search, read/write, and sandboxed code execution tools."""

import os
import re
import subprocess
import sys
import warnings

from google.adk.agents import Agent
from google.genai import types

# The default model, shared with eval.py so there is a single source of truth.
DEFAULT_MODEL = "gemini-3.1-flash-lite"

# Silencing an ADK warning to declutter terminal output
warnings.filterwarnings("ignore", message=r".*JSON_SCHEMA_FOR_FUNC_DECL.*", category=UserWarning)


def _resolve(sandbox: str, path: str) -> str:
    """Turn a sandbox-relative path into an absolute one, refusing to escape the sandbox."""
    sandbox = os.path.realpath(sandbox)
    full = os.path.realpath(os.path.join(sandbox, path))
    # Allow only the sandbox root itself or a path beneath it (blocks "../" escapes).
    if full != sandbox and not full.startswith(sandbox + os.sep):
        raise ValueError(f"path escapes sandbox: {path!r}")
    return full


# The helpers below return errors as plain strings/dicts instead of raising, so the
# model sees what went wrong and can recover on its next turn.

def _read(sandbox: str, path: str) -> str:
    try:
        with open(_resolve(sandbox, path), encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return f"Error: no such file: {path}"
    except (ValueError, OSError) as exc:
        return f"Error: {exc}"


def _write(sandbox: str, path: str, contents: str) -> str:
    try:
        full = _resolve(sandbox, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(contents)
    except (ValueError, OSError) as exc:
        return f"Error: {exc}"
    return f"Wrote {len(contents)} chars to {path}"


def _list_files(sandbox: str, directory: str = ".") -> str:
    try:
        target = _resolve(sandbox, directory)
        if not os.path.exists(target):
            return f"Error: no such directory: {directory}"
        files = []
        for root, dirs, filenames in os.walk(target):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git", ".venv"))
            for fname in sorted(filenames):
                if fname.endswith(".pyc"):
                    continue
                rel = os.path.relpath(os.path.join(root, fname), sandbox)
                files.append(rel)
        return "\n".join(files) if files else "(empty directory)"
    except (ValueError, OSError) as exc:
        return f"Error: {exc}"


def _search_code(sandbox: str, pattern: str, directory: str = ".") -> str:
    try:
        target = _resolve(sandbox, directory)
        if not os.path.exists(target):
            return f"Error: no such directory: {directory}"
        regex = re.compile(pattern)
        matches = []
        for root, dirs, filenames in os.walk(target):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git", ".venv"))
            for fname in sorted(filenames):
                if fname.endswith(".pyc"):
                    continue
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, sandbox)
                try:
                    with open(full, encoding="utf-8") as fh:
                        for lineno, line in enumerate(fh, 1):
                            if regex.search(line):
                                matches.append(f"{rel}:{lineno}: {line.rstrip()}")
                except OSError:
                    continue
        return "\n".join(matches) if matches else "No matches found."
    except (ValueError, re.error, OSError) as exc:
        return f"Error: {exc}"


def _run_command(sandbox: str, command: str, stdin_data: str = "") -> dict:
    """Execute a shell command inside the sandbox directory and capture stdout, stderr, and exit code."""
    try:
        real_sandbox = os.path.realpath(sandbox)
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": f"{real_sandbox}:{os.path.join(real_sandbox, 'src')}",
        }
        proc = subprocess.run(
            command,
            shell=True,
            cwd=real_sandbox,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Error: Command timed out after 15s"}
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": f"Error: {exc}"}


def _run_python(sandbox: str, code: str, stdin_data: str = "") -> dict:
    """Execute a Python snippet inside the sandbox directory and capture stdout, stderr, and exit code."""
    try:
        real_sandbox = os.path.realpath(sandbox)
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": f"{real_sandbox}:{os.path.join(real_sandbox, 'src')}",
        }
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=real_sandbox,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Error: Python execution timed out after 15s"}
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": f"Error: {exc}"}


SYSTEM_INSTRUCTION = """You are an autonomous software engineering agent. Follow this disciplined workflow on every task:

1. EXPLORE & TRACE ROOT CAUSES BEFORE EDITING (BUG-FIX TASKS):
   - Always start by calling `list_files` to inspect the workspace structure.
   - If existing source files are present in `src/`, NEVER assume the bug is in the single file or function named in the prompt.
   - Read ALL files in the package (including `__init__.py` and sibling helper modules such as parsing, loading, or data-ingestion helpers) using `read_file` or `search_code` before making any edits.
   - Trace the full data flow upstream from where raw inputs are parsed/loaded to where results are computed. Fix the true root cause in the upstream module rather than patching symptoms downstream.
   - CRITICAL FOR BUG-FIX TASKS: Make the minimal fix in the upstream helper only (e.g. removing an unwanted `int(...)` cast around `float(raw)` or removing `.replace(tzinfo=None)`), and leave the downstream module untouched. NEVER change return types from `float` to `Decimal` in existing library functions, because tests compare return values directly against `float` literals with `==` (and `Decimal('125.49') == 125.49` evaluates to `False` in Python).

2. IMPLEMENT WITH RIGOR ON EDGE CASES & OUTPUT CONTRACTS (BUILD-FROM-SCRATCH CLI TASKS):
   - Always use `write_file` to save your code to the required file path. Never just print code in your final response without calling `write_file`.
   - Enumerate and handle boundary conditions systematically:
     * Sequence & range direction: Support both ascending (`a <= b`) and descending/reversed ranges (e.g., `9-7` must expand in descending order `9 8 7` when `start > end`), single values, and `start == end`.
     * Numeric precision & money rounding (for CLI programs built from scratch): When building a standalone CLI script that formats money or decimal intervals to stdout, use `decimal.Decimal` initialized from strings (not `float`). For half-up rounding to two decimal places, use `.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` (so `5.005` rounds to `5.01` and `3.675` rounds to `3.68`). Always pass a `Decimal("0")` start value to `sum(..., Decimal("0"))` so empty inputs return `Decimal("0")` instead of integer `0`.
     * Trailing-zero trimming: To format a `Decimal` with trailing zeros trimmed (e.g., `4.0` -> `4`, `1.50` -> `1.5`), use `format(val, "f")` and strip trailing `"0"` and `"."` only when `"."` is present (avoid `.normalize()`, which turns multiples of 10 like `10.0` into scientific notation `1E+1`).
     * Empty & blank inputs: Handle empty stdin and blank lines explicitly according to the specification (e.g., printing nothing on empty range input, or `0.00` for totals/averages/lengths on empty records).
     * Exact exit codes & stderr: For invalid commands, missing arguments, missing categories, or malformed input lines (wrong field count, unparseable numbers, or `start > end` where disallowed), print an error message to `sys.stderr` (never `stdout`) and exit with the exact required code (`sys.exit(2)` or `sys.exit(1)`).

3. VERIFY BY EXECUTING CODE & TESTS BEFORE FINISHING:
   - Never finish without executing and testing your code via `run_python` or `run_command`.
   - For bug fixes: first reproduce the failure across the full pipeline (calling upstream load/parse functions and passing their output to downstream functions), apply the minimal fix to the upstream root cause, and re-run to confirm `isinstance(result, float)` or `isinstance(result, int)` and exact `==` equality with the expected Python literal.
   - For CLI programs: use `run_command` with `stdin_data` to test every subcommand, every example in the prompt, and all edge cases (empty input, blank lines, descending ranges like `9-7`, touching intervals, half-up rounding ties like `.005` or `.675`, missing lookup keys, and malformed inputs verifying both `stderr` and `returncode`).
   - If any check fails, diagnose the error, update the file with `write_file`, and re-verify until all tests pass. Do not leave temporary test files inside `src/`.
"""


def build_agent(sandbox: str, model: str) -> Agent:
    # Each tool's docstring is the description the model sees, so it states that
    # paths are sandbox-relative.
    def list_files(directory: str = ".") -> dict:
        """List all files recursively under a directory relative to the project root."""
        return {"result": _list_files(sandbox, directory)}

    def search_code(pattern: str, directory: str = ".") -> dict:
        """Search for a regex pattern across files in a directory relative to the project root."""
        return {"result": _search_code(sandbox, pattern, directory)}

    def read_file(path: str) -> dict:
        """Read a text file (path is relative to the project root) and return its contents."""
        return {"result": _read(sandbox, path)}

    def write_file(path: str, contents: str) -> dict:
        """Create or overwrite a text file (path is relative to the project root)."""
        return {"result": _write(sandbox, path, contents)}

    def run_command(command: str, stdin_data: str = "") -> dict:
        """Run a shell/CLI command in the project root with optional stdin_data, returning returncode, stdout, and stderr."""
        return _run_command(sandbox, command, stdin_data)

    def run_python(code: str, stdin_data: str = "") -> dict:
        """Execute a Python code snippet (`python -c`) in the project root with optional stdin_data, returning returncode, stdout, and stderr."""
        return _run_python(sandbox, code, stdin_data)

    return Agent(
        name="coding_agent",
        model=model,
        instruction=SYSTEM_INSTRUCTION,
        tools=[list_files, search_code, read_file, write_file, run_command, run_python],
        generate_content_config=types.GenerateContentConfig(
            temperature=0.0,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.LOW
            ),
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=5,
                    initial_delay=1.0,
                    max_delay=10.0,
                )
            ),
        )
    )


if __name__ == "__main__":
    # Test the agent on a prompt in ./out sandbox.  Usage: python agent.py "your prompt"
    import asyncio
    from google.adk.runners import InMemoryRunner

    # Default to Vertex AI (like eval.py) so `python agent.py` works without a
    # Gemini API key; an existing env value, if set, takes precedence.
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-01-ee4907279711")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

    sandbox = os.path.join(os.path.dirname(os.path.realpath(__file__)), "out")
    os.makedirs(os.path.join(sandbox, "src"), exist_ok=True)
    prompt = " ".join(sys.argv[1:]) or "Write a hello world python script"

    async def _run_agent() -> None:
        runner = InMemoryRunner(agent=build_agent(sandbox, DEFAULT_MODEL))
        session = await runner.session_service.create_session(
            app_name=runner.app_name, user_id="me")
        message = types.Content(role="user", parts=[types.Part(text=prompt)])
        async for event in runner.run_async(user_id="me", session_id=session.id, new_message=message):
            for part in (event.content and event.content.parts) or []:
                print(part.text or "", end="", flush=True)
    asyncio.run(_run_agent())
    import glob
    for script in glob.glob(f"{sandbox}/**/*.py", recursive=True):
        print(f"\n=== output of {os.path.relpath(script, sandbox)} ===\n" + subprocess.run([sys.executable, script], cwd=sandbox, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout, end="")

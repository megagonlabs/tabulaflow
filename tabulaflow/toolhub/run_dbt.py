"""Run-dbt tool for dbt agents.

Provides a controlled interface to execute dbt CLI commands (``run``,
``build``, ``test``, ``compile``, ``debug``, ``ls``) scoped to a working
directory.  The tool auto-injects ``--project-dir`` and ``--profiles-dir``
and prevents arbitrary shell execution.
"""

import asyncio
import logging
import shutil
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel
from pydantic_ai import Tool

logger = logging.getLogger(__name__)

MAX_OUTPUT_CHARS = 30000

DbtCommand = Literal["run", "build", "test", "compile", "debug", "ls", "deps"]


class RunDbtToolMetrics(BaseModel):
    num_run: int = 0
    num_build: int = 0
    num_test: int = 0
    num_compile: int = 0
    num_debug: int = 0
    num_ls: int = 0
    num_deps: int = 0
    error_count: int = 0
    num_run_success: int = 0
    num_run_failure: int = 0
    last_run_success: bool | None = None


class RunDbtTool:
    """Execute dbt CLI commands in a project working directory.

    The tool automatically sets ``--project-dir`` and ``--profiles-dir`` to
    the working directory, ensuring dbt always operates on the correct
    project.  Only a fixed set of subcommands is allowed.

    An optional ``pre_run_hook`` can be supplied (e.g. to restore a pristine
    database before each build).  The hook is invoked only before ``run`` and
    ``build`` commands, which re-materialise all models; read-only commands
    such as ``test``, ``ls``, and ``compile`` skip the hook so they operate
    on the database state left by the most recent build.

    Attributes:
        working_dir: Path to the dbt project directory.
        pre_run_hook: Optional async callback invoked before ``run`` and
            ``build`` commands (e.g. to restore a pristine database).
    """

    name: ClassVar = "run_dbt"

    def __init__(
        self,
        working_dir: str,
        pre_run_hook: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._working_dir = Path(working_dir).resolve()
        if not self._working_dir.is_dir():
            raise ValueError(f"working_dir is not a directory: {working_dir}")
        self._dbt_path = self._find_dbt()
        self._metrics = RunDbtToolMetrics()
        self._pre_run_hook = pre_run_hook

    @staticmethod
    def _find_dbt() -> str:
        """Locate the ``dbt`` binary.

        Checks ``PATH`` first (covers global installs, Homebrew, conda,
        activated venvs, etc.), then falls back to the current Python
        environment's ``bin/`` directory for cases where the venv is not
        activated but dbt is installed in it.
        """
        found = shutil.which("dbt")
        if found:
            return found
        venv_dbt = Path(sys.prefix) / "bin" / "dbt"
        if venv_dbt.is_file():
            return str(venv_dbt)
        return "dbt"

    def _error(self, msg: str) -> str:
        self._metrics.error_count += 1
        return f"(error: {msg})"

    def _increment_counter(self, command: DbtCommand) -> None:
        attr = f"num_{command}"
        setattr(self._metrics, attr, getattr(self._metrics, attr) + 1)

    async def __call__(
        self,
        command: DbtCommand,
        select: str | None = None,
        exclude: str | None = None,
    ) -> str:
        """Run a dbt CLI command in the project directory.

        Args:
            command: The dbt subcommand to run. One of ``"run"``, ``"build"``,
                ``"test"``, ``"compile"``, ``"debug"``, ``"ls"``, ``"deps"``.
            select: Optional ``--select`` node selector (e.g. ``"my_model"``
                or ``"tag:daily"``).  Applies to ``run``, ``build``, ``test``,
                ``compile``, and ``ls``.
            exclude: Optional ``--exclude`` node selector.  Same commands as
                ``select``.
        """
        self._increment_counter(command)

        cmd_parts = [
            self._dbt_path,
            command,
            "--no-use-colors",
            "--project-dir",
            str(self._working_dir),
            "--profiles-dir",
            str(self._working_dir),
        ]

        supports_selection = command in ("run", "build", "test", "compile", "ls")
        if select:
            if not supports_selection:
                return self._error(f"--select is not supported for 'dbt {command}'.")
            cmd_parts += ["--select", select]
        if exclude:
            if not supports_selection:
                return self._error(f"--exclude is not supported for 'dbt {command}'.")
            cmd_parts += ["--exclude", exclude]

        logger.debug("run_dbt: %s", " ".join(cmd_parts))

        if self._pre_run_hook is not None and command in ("run", "build"):
            await self._pre_run_hook()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self._working_dir),
            )
            stdout_bytes, _ = await proc.communicate()
            output = stdout_bytes.decode("utf-8", errors="replace")
        except FileNotFoundError:
            return self._error("dbt command not found. Ensure dbt is installed and on PATH.")
        except Exception as e:
            return self._error(f"Failed to execute dbt: {e}")

        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + f"\n\n(output truncated at {MAX_OUTPUT_CHARS} chars)"

        exit_code = proc.returncode
        if command in ("run", "build"):
            success = exit_code == 0
            self._metrics.last_run_success = success
            if success:
                self._metrics.num_run_success += 1
            else:
                self._metrics.num_run_failure += 1

        header = f"dbt {command} exited with code {exit_code}\n"
        return header + output

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> RunDbtToolMetrics:
        return self._metrics

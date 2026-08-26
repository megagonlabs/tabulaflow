# Concurrent `execute_bash` — Design Proposal

Status: implemented.

## Goal

Replace the shared persistent PTY with independent non-PTY Bash jobs. Calls may
run concurrently, while commands that outlive a tool call remain observable and
controllable through ordinary `execute_bash` calls.

The design prioritizes a small model-facing API, predictable process ownership,
and preservation of expensive work when waiting times out.

## Public API

```python
async def execute_bash(
    command: str,
    mode: Literal[
        "kill_on_timeout",
        "detach_on_timeout",
        "background",
    ] = "detach_on_timeout",
    wait_timeout: float | None = None,
) -> str:
    ...
```

Modes:

| Mode | Behavior |
|---|---|
| `kill_on_timeout` | Wait for completion; terminate the process group when the wait budget expires. |
| `detach_on_timeout` | Wait for completion; return a running job when the wait budget expires. This is the default. |
| `background` | Return a running job immediately. `wait_timeout` does not apply. |

`wait_timeout` is a wall-clock wait budget, not an inactivity timeout. When it
is omitted, waiting modes use the tool's configured default. Supplying it with
`background` is an error.

Remove `is_input` and `reset`. Interactive programs can be run explicitly with
Python's `pty` module or tmux when needed.

## Execution model

Every invocation creates an independent job and process group:

```python
process = await asyncio.create_subprocess_exec(
    bash_path,
    "-c",
    command,
    cwd=working_dir,
    env=env,
    stdin=asyncio.subprocess.DEVNULL,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
    start_new_session=True,
)
```

Do not use `-i` or `-l`; shell startup files must not mutate the inherited
environment or produce startup output. Each call starts in `working_dir`.
Filesystem changes persist, but shell state such as cwd, variables, functions,
and activated environments does not. Commands that need shared shell state
should express it in one invocation, for example:

```bash
cd subproject && source .venv/bin/activate && pytest
```

There is no execution-wide lock. A small lock protects only job ID allocation
and the in-memory job registry.

## Environment

Snapshot `os.environ` when the tool is constructed and apply only explicit
caller-provided overrides:

```python
env = os.environ.copy()
env.update(env_overrides or {})
```

This preserves the launch environment, including PATH, direnv configuration,
virtual environments, proxies, and cloud credentials. Do not add pager,
terminal, Git-prompt, or Python-buffering overrides by default; non-PTY
execution already handles most pager behavior, and commands can opt into local
overrides when necessary.

Constructor-owned configuration should include:

```python
ExecuteBashTool(
    working_dir=project_dir,
    job_dir=scratch_dir / "bash-jobs",
    env_overrides={"SCRATCH": str(scratch_dir)},
)
```

`job_dir` is explicit rather than inferred from `SCRATCH`. Research callers can
provide additional overrides, such as an adjusted dbt `PATH`. This replaces
`init_commands`.

## Job identity and logs

Allocate short, session-local IDs synchronously before spawning:

```text
J1, J2, J3, ...
```

Random IDs are unnecessary because the scratch directory already isolates one
session. Open each path exclusively and advance past an existing ID if a scratch
directory is reused.

Store logs outside the project:

```text
$SCRATCH/bash-jobs/J1.log
$SCRATCH/bash-jobs/J2.log
```

Create `bash-jobs` with mode `0700` and logs with mode `0600`. The filesystem is
the correct storage layer because job output is mutable and incrementally
written. Do not store live logs in `MessageStore`, which owns immutable
model-facing messages persisted as workspace rows.

Drain stdout/stderr continuously so a noisy child cannot block on a full pipe.
Retain a bounded head-and-tail snapshot in the log and in the tool return; do
not allow detached output to grow without bound. The exact snapshot update
mechanism is internal, but the visible log must remain valid text throughout
execution.

When the process ends, append one manager-generated final non-empty line:

```text
[bash_job: J1, state: exited, exit_code: 0]
```

or:

```text
[bash_job: J1, state: killed, signal: 15]
```

Absence of the footer means the job is still running. The in-memory registry,
not log parsing, remains the runtime source of truth. A separate status file is
not needed.

## Tool results

A completed call returns its bounded output followed by the existing exit-code
footer:

```text
...
[exit_code: 0]
```

A detached or background call returns available output plus stable management
metadata:

```text
Command is still running.

[job_id: J1]
[process_group: 12345]
[log: /.../scratch/bash-jobs/J1.log]
```

Do not report a current working directory because a child's final cwd does not
affect later calls.

## Inspecting and stopping jobs

Do not add a separate job-management tool initially. The agent uses ordinary
`execute_bash` calls:

```bash
tail -n 50 "$SCRATCH/bash-jobs/J1.log"
```

```bash
kill -TERM -- -12345
```

The negative ID signals the entire process group, including descendants. If the
group does not stop after a grace period, the agent may use `SIGKILL`:

```bash
kill -KILL -- -12345
```

## Timeout, cancellation, and close

For `kill_on_timeout`, send `SIGTERM` to the process group, wait briefly, then
send `SIGKILL` if necessary. Return partial output with `exit_code: -1`.

For `detach_on_timeout`, stop waiting and return job metadata without signaling
the process. The collector and waiter continue in the background.

If the caller is cancelled before it receives a detached job result, terminate
the process group and re-raise `CancelledError`; otherwise work could continue
without the agent learning its job ID.

All jobs are session-owned. `ExecuteBashTool.close()` terminates remaining jobs,
waits for collectors, appends terminal footers, and releases resources.
`background` means background relative to the tool call, not a system daemon
that survives TabulaFlow. An agent that intentionally needs that behavior can
use `nohup` or tmux explicitly.

## Resource guidance

Do not enforce a hard active-job limit initially. A hard limit would need a
separate control lane so the agent could still run `tail` or `kill` commands
after capacity was reached.

Instead, define a soft warning threshold, initially eight jobs returned as
running. Calls continue to run, but detached/background results include a
concise warning and reported-running job IDs:

```text
[warning: 9 detached shell jobs are currently running: J1, J2, J4, J5, J6, J7, J8, J9, J10]
```

Remove completed jobs from the active set immediately and update the registry
atomically. This is a cooperative guardrail, consistent with the existing
command filter rather than a resource sandbox. A generous emergency ceiling can
be added later if real usage shows runaway accumulation.

## Safety and compatibility

Keep the existing command filter and apply it before job creation. Continue to
run only on POSIX systems with Bash available. Never include the complete
inherited environment in tool output or logs. Strip ANSI/OSC sequences and
unsafe terminal controls from rendered tool output and logs while preserving
newlines and tabs; commands that need raw bytes can redirect them explicitly.

The new runner intentionally drops these persistent-PTY behaviors:

- cross-call cwd and environment mutation;
- raw stdin interaction and control-key forwarding;
- prompt-sentinel parsing;
- terminal echo handling required specifically by a PTY;
- multiline command staging;
- shell reset and recovery state.

Multiline commands are passed directly as the single argument to `bash -c`.
Common terminal-only needs remain available through explicit Python PTY or tmux
commands.

## Implementation shape

Keep the runtime split small:

```text
ExecuteBashTool
  - validates model-facing arguments
  - allocates a job ID
  - starts a BashJob
  - waits according to mode
  - formats the tool result

BashJob
  - owns process/process-group metadata
  - drains bounded output to J<n>.log
  - records state and exit status
  - terminates the process group
```

This is an internal job abstraction, not a broad public result hierarchy.

## Verification

Replace persistent-session tests with coverage for:

- truly concurrent commands with isolated output and exit codes;
- inherited environment plus explicit overrides;
- fresh cwd and environment on every call;
- multiline commands without staging;
- bounded large output and split UTF-8 reads;
- `kill_on_timeout` process-group termination;
- `detach_on_timeout` progress, footer, and later completion;
- immediate `background` return;
- manual process-group termination through another shell call;
- cancellation cleanup before a job result is returned;
- concurrent job ID allocation;
- active-job warnings;
- session-close cleanup;
- command-filter behavior;
- log permissions and absence of project-directory artifacts.

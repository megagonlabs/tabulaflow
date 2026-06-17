"""A small denylist guard for the shell tool.

This is a GUARDRAIL against a cooperative agent accidentally running a catastrophic
command on the user's machine — NOT a security sandbox. The patterns are intentionally
narrow (rarely-legitimate, irreversible operations); a determined or obfuscated command
can bypass them, and that is an accepted limitation. Plug it into ``ExecuteBashTool`` via
``command_filter=dangerous_command_reason``.
"""

from __future__ import annotations

import re

# (pattern, reason) pairs — kept small and high-signal on purpose. Each matches a
# class of "you almost certainly didn't mean to do this" command.
_DANGEROUS: list[tuple[re.Pattern[str], str]] = [
    # rm -r/-rf whose target is the root, a root glob, the home dir, or the current/
    # parent dir (bare). Specific subpaths like `rm -rf ./build` or `/tmp/x` are allowed.
    (
        re.compile(r"\brm\b(?=[^\n|;&]*\s-[A-Za-z]*[rf])[^\n|;&]*?\s(/\*?|~|\$HOME|\.\.?)(?=\s|$)"),
        "recursive delete of the root, home, or current/parent directory",
    ),
    # Classic fork bomb.
    (re.compile(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:?\s*&\s*\}\s*;\s*:"), "fork bomb"),
    # Formatting / repartitioning a filesystem or disk.
    (
        re.compile(r"\b(mkfs(\.\w+)?|fdisk|parted|diskutil\s+(eraseDisk|reformat|partitionDisk))\b"),
        "filesystem/partition modification",
    ),
    # Raw writes to a device node (via dd or a redirect).
    (re.compile(r"\bdd\b[^\n]*\bof=\s*/dev/"), "raw write to a device with dd"),
    (re.compile(r">\s*/dev/(sd|nvme|disk|hd)\w*"), "write to a block device"),
    # Piping a downloaded script straight into a shell.
    (
        re.compile(r"\b(curl|wget|fetch)\b[^\n|]*\|\s*(sudo\s+)?(ba|z|fi|da|c)?sh\b"),
        "piping a download into a shell (remote code execution)",
    ),
    # Git operations that silently discard uncommitted work.
    (
        re.compile(r"\bgit\b[^\n]*\b(reset\s+--hard|checkout\s+(--\s+)?\.|clean\s+-[A-Za-z]*f)"),
        "destructive git operation that discards uncommitted changes",
    ),
    # Overwriting a system path via redirect.
    (re.compile(r">\s*/(etc|bin|sbin|usr|boot|sys|lib|System|Library)\b"), "overwrite of a system path"),
    # Powering off / rebooting the machine.
    (re.compile(r"\b(shutdown|reboot|halt|poweroff)\b|\binit\s+[06]\b"), "machine power control"),
    # Privilege escalation.
    (re.compile(r"\bsudo\b"), "privilege escalation (sudo)"),
]


def dangerous_command_reason(command: str) -> str | None:
    """Return a short reason if ``command`` matches a catastrophic-action pattern, else None.

    Suitable as an ``ExecuteBashTool`` ``command_filter``: returning a reason blocks the
    command (the reason is surfaced to the agent), returning None allows it.
    """
    for pattern, reason in _DANGEROUS:
        if pattern.search(command):
            return reason
    return None

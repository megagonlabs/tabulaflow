import argparse


def bool_flag(value: str) -> bool:
    """Parse boolean flags from command line arguments.

    Supports: true/false, yes/no, 1/0 (case-insensitive).
    Use with `type=bool_flag` in argparse to allow `--flag true` / `--flag false`.
    """
    if value.lower() in ("true", "yes", "1"):
        return True
    elif value.lower() in ("false", "no", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError(f"Boolean value expected, got '{value}'")

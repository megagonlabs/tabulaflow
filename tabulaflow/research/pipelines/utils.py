import argparse
from typing import Any, Coroutine

from tqdm.asyncio import tqdm_asyncio


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


def _flatten_dict(data: dict[str, Any], sep: str = ".") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result.update(
                {
                    f"{key}{sep}{nested_key}": nested_value
                    for nested_key, nested_value in _flatten_dict(value, sep).items()
                }
            )
        else:
            result[key] = value
    return result


def pprint_dict(data: dict[str, Any]) -> str:
    """Format nested numeric metrics as a flat Markdown list."""
    return "\n".join(
        f"- {key}: {'N/A' if value is None else f'{value:.4f}'}" for key, value in _flatten_dict(data).items()
    )


async def tqdm_gather_with_exceptions(
    *fs: Coroutine[Any, Any, Any], return_exceptions: bool = False, **kwargs: Any
) -> list[Any]:
    """Gather coroutines with tqdm progress and optional exception values."""
    if not return_exceptions:
        return await tqdm_asyncio.gather(*fs, **kwargs)  # type: ignore[no-any-return]

    async def wrap(f: Coroutine[Any, Any, Any]) -> Any:
        try:
            return await f
        except Exception as exc:
            return exc

    return await tqdm_asyncio.gather(*map(wrap, fs), **kwargs)  # type: ignore[no-any-return]

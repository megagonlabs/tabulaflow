import pandas as pd
import re
from tabulate import tabulate


def format_df(
    df: pd.DataFrame, *, max_visible_rows: int = 10, max_cell_width: int = 200, tablefmt: str = "github"
) -> str:
    def truncate_cell(val: object) -> object:
        if pd.isna(val):
            return "[NULL]"  # Convert all nulls to string (pandas coerces None back to nan/NaT)
        if isinstance(val, str) and len(val) > max_cell_width:
            half = max_cell_width // 2
            return val[:half] + "..." + val[-half:]
        return val

    # Apply truncation first to preserve numeric types (nulls stay as None for tabulate)
    display_df = df.map(truncate_cell)

    n = len(display_df)
    if n > max_visible_rows:
        first_n = (max_visible_rows + 1) // 2
        last_n = max_visible_rows - first_n
        head_df = display_df.head(first_n)
        tail_df = display_df.tail(last_n)
        ellipsis_row = pd.DataFrame([["..."] * len(df.columns)], columns=df.columns)
        display_df = pd.concat([head_df, ellipsis_row, tail_df], ignore_index=True)

    # showindex=False hides the automatic row numbers
    return tabulate(display_df, headers="keys", tablefmt=tablefmt, showindex=False, missingval="[NULL]")


def equals_ci(a: str | None, b: str | None) -> bool:
    """
    Compare two strings case-insensitively, treating None == None.
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.lower() == b.lower()


def format_sqlalchemy_error_msg(error_msg: str) -> str:
    error_msg = re.sub(r"\[SQL:.*?\]", "", error_msg)
    error_msg = re.sub(r"\[parameters:.*?\]", "", error_msg)
    error_msg = re.sub(r"\(Background on this error at: https://sqlalche\.me/e/\S+\)", "", error_msg)
    return error_msg.strip()

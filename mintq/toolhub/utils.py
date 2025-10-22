import pandas as pd
import numpy as np
import re
from tabulate import tabulate


def format_df(df: pd.DataFrame, *, max_visible_rows: int = 5, tablefmt: str = "simple") -> str:
    n = len(df)
    if n > max_visible_rows:
        first_n = (max_visible_rows + 1) // 2
        last_n = max_visible_rows - first_n
        head = df.head(first_n)
        tail = df.tail(last_n)
        ellipsis_row = {col: "..." for col in df.columns}
        display_df = pd.concat([head, pd.DataFrame([ellipsis_row]), tail], ignore_index=True)
    else:
        display_df = df

    display_df = display_df.replace({np.nan: "[null]"})

    # showindex=False hides the automatic row numbers
    return tabulate(display_df, headers="keys", tablefmt=tablefmt, showindex=False, missingval="[null]")


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

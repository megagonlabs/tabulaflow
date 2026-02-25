import re


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
    error_msg = re.sub(r"\[SQL:.*?\]", "", error_msg, flags=re.DOTALL)
    error_msg = re.sub(r"\[parameters:.*?\]", "", error_msg, flags=re.DOTALL)
    error_msg = re.sub(r"\(Background on this error at: https://sqlalche\.me/e/\S+\)", "", error_msg, flags=re.DOTALL)
    return error_msg.strip()

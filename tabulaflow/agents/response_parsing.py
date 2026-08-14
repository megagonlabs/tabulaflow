import re


def extract_code(response: str) -> str:
    match = re.search(r"```(?:([\w+-]+))?\n([\s\S]*?)\n```", response)
    return match.group(2).strip() if match else response.strip()

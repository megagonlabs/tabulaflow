from pathlib import Path


def main() -> None:
    trajectory_dirs = [path for path in Path.home().glob(".tabulaflow/sessions/*/trajectories") if path.is_dir()]
    if not trajectory_dirs:
        return

    latest_dir = max(trajectory_dirs, key=lambda path: path.stat().st_mtime)
    files = sorted(
        (path for path in latest_dir.rglob("*") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in files:
        print(path)


if __name__ == "__main__":
    main()

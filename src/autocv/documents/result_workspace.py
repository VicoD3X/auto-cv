from pathlib import Path
import shutil


def copy_to_result(source_path: Path, target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.resolve() == target_path.resolve():
        return target_path
    shutil.copy2(source_path, target_path)
    return target_path


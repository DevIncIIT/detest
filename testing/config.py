from pathlib import Path

DETEST_GLOBAL = Path("~/.detest").expanduser()
DETEST_IMAGES = DETEST_GLOBAL / "images"
DETEST_PROJECTS = DETEST_GLOBAL / "projects"
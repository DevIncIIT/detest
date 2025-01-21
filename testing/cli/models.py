from pydantic import BaseModel
from typing import Callable


class Commands(BaseModel):
    build: str
    run: str
    migrate: str


class ProjectConfig(BaseModel):
    path_to_project: str
    project_name: str
    project_url: str
    parallel_execution: int
    environment_variables: dict[str, str]
    commands: Commands


def environment_variables_to_string(
    environment_variables: dict[str, str], value_parser: Callable[[str], str] | None = None
) -> str:
    if value_parser is None:
        value_parser = lambda x: x
    
    return " ".join([f"{key}={value_parser(value)}" for key, value in environment_variables.items()])

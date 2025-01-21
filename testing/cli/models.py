from pydantic import BaseModel


class Commands(BaseModel):
    build: str
    run: str
    migrate: str


class ProjectConfig(BaseModel):
    path_to_project: str
    project_name: str
    parallel_execution: int
    environment_variables: dict[str, str]
    commands: Commands


def environment_variables_to_string(environment_variables: dict[str, str]) -> str:
    return " ".join([f"{key}={value}" for key, value in environment_variables.items()])

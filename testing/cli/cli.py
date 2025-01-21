import os

import click
from pydantic import BaseModel, ValidationError


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


@click.group()
def cli():
    """CLI tool for managing test projects"""
    pass


@cli.command()
def create():
    """Interactive CLI to create a new test project"""

    # Get project name
    print("Enter project name: ", end="")
    project_name = input().strip()

    print("Enter path to project: ", end="")
    path_to_project = input().strip()

    if not project_name:
        print("Error: Project name cannot be empty")
        return

    # Create project directory
    try:
        os.makedirs(project_name)
        os.makedirs(os.path.join(project_name, "tests"))
    except FileExistsError:
        print(f"Error: Project {project_name} already exists")
        return

    # Configure default settings
    config = ProjectConfig(
        path_to_project=path_to_project,
        project_name=project_name,
        parallel_execution=1,
        environment_variables={},
        commands=Commands(build="", run="", migrate=""),
    )

    # Write config file
    config_path = os.path.join(project_name, "config.json")
    with open(config_path, "w") as f:
        f.write(config.model_dump_json(indent=4))

    print(
        f"""
Project {project_name} created successfully!
Structure:
{project_name}/
├── config.json
└── tests/
"""
    )


@cli.command()
def init():
    """Read and display the project configuration"""
    try:
        with open("config.json") as f:
            config_data = ProjectConfig.model_validate_json(f.read())
            print(config_data.model_dump_json(indent=4))
    except FileNotFoundError:
        print("Error: config.json not found in current directory")
        return
    except ValidationError:
        print("Error: Invalid configuration in config.json")
        return

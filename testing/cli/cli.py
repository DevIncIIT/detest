import os
import click

from pydantic import ValidationError
from subprocess import run, PIPE

from testing.config import DETEST_PROJECTS
from testing.containers.db import download_db_image, create_db_container
from testing.cli.models import ProjectConfig, Commands, environment_variables_to_string


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

    dl_success = download_db_image()
    if not dl_success:
        print("Error: Failed to download database image")
        return

    print("Database image downloaded successfully")


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
    
    if not config_data.commands.migrate or not config_data.path_to_project:
        print("Error: Commands or path to project not found in config.json")
        return

    db_urls = create_db_container(1)
    if not db_urls:
        print("Error: Failed to create database container")
        return

    print(f"Database container created successfully: {db_urls}")

    os.system(
        f"cd {DETEST_PROJECTS} && git clone {config_data.path_to_project} {config_data.project_name}"
    )

    env_vars = environment_variables_to_string(config_data.environment_variables)
    command_to_run = f'{env_vars} {config_data.commands.migrate}'

    os.system(f"cd {DETEST_PROJECTS / config_data.project_name} && {command_to_run}")
    print("Database migrated successfully. Proceeding to extract schema")

    output = run(f"sqlacodegen {db_urls[0]}", stdout=PIPE).stdout.decode("utf-8")
    with open("schema.py", "w") as f:
        f.write(output)

    print("Schema extracted successfully")

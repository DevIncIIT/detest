import importlib.util
import os
import signal
import click

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pydantic import ValidationError
from subprocess import run, PIPE, Popen

from testing import TestCase
from testing.config import DETEST_PROJECTS
from testing.containers.db import (
    create_db_container,
    drop_db_container,
)
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
        project_url="",
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


def read_config():
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
    return config_data


@cli.command()
def init():
    """Read and display the project configuration"""

    config_data = read_config()
    if not config_data:
        print("Error: Failed to read config.json")
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
    command_to_run = f"{env_vars} {config_data.commands.migrate}"

    os.system(f"cd {DETEST_PROJECTS / config_data.project_name} && {command_to_run}")
    print("Database migrated successfully. Proceeding to extract schema")

    output = run(f"sqlacodegen {db_urls[0]}", stdout=PIPE).stdout.decode("utf-8")

    if not drop_db_container():
        print("Error: Failed to drop database container")
        return

    with open("schema.py", "w") as f:
        f.write(output)

    print("Schema extracted successfully")


def discover_subclasses_from_folder():
    subclasses = []
    folder_path = "tests/"
    for filename in os.listdir(folder_path):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]  # Remove the .py extension
            module_path = os.path.join(folder_path, filename)

            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None:
                continue
            module = importlib.util.module_from_spec(spec)
            loader = spec.loader
            if loader is None:
                continue
            loader.exec_module(module)

            # Discover subclasses
            for name in dir(module):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, TestCase)
                    and obj is not TestCase
                ):
                    subclasses.append(obj)
    return subclasses


@cli.command()
def test():
    confdata = read_config()
    if not confdata:
        print("Error: Failed to read config.json")
        return

    test_cases = discover_subclasses_from_folder()

    db_urls = create_db_container(len(test_cases))
    if not db_urls:
        print("Error: Failed to create database container")
        return

    env_vars = environment_variables_to_string(
        confdata.environment_variables,
        value_parser=lambda x: db_urls[0] if x == "$DB_URL" else x,
    )

    process = Popen(
        f"cd {DETEST_PROJECTS / confdata.project_name} && {confdata.commands.migrate} && {confdata.commands.build} && {env_vars} {confdata.commands.run}",
        shell=True,
        preexec_fn=os.setsid,
    )
    pid = process.pid

    for i, test_case in enumerate(test_cases):
        session = Session(bind=create_engine(db_urls[i]))
        tc = test_case(url=confdata.project_url, session=session)

        try:
            tc.run()
        except AssertionError as e:
            print(f"Error: {e}")
        print(f"Test {test_case.__name__} passed")

        session.close()

    os.killpg(os.getpgid(pid), signal.SIGTERM)
    print("Server process killed successfully")

    if not drop_db_container():
        print("Error: Failed to drop database container")
        return

    print("Database container dropped successfully")

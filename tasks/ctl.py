from invoke import Context, task

from .shared import (
    BUILD_NAME,
    NBR_WORKERS,
    build_test_compose_files_cmd,
    execute_command,
    get_env_vars,
)
from .utils import REPO_BASE

MAIN_DIRECTORY = "ctl"
NAMESPACE = "CTL"


# ----------------------------------------------------------------------------
# Documentation
# ----------------------------------------------------------------------------
@task
def generate_doc(context: Context):
    """Generate the documentation for infrahubctl using typer-cli."""

    CLI_COMMANDS = (
        ("infrahub_ctl.branch", "infrahubctl branch", "10_infrahubctl_branch"),
        ("infrahub_ctl.schema", "infrahubctl schema", "20_infrahubctl_schema"),
        ("infrahub_ctl.validate", "infrahubctl validate", "30_infrahubctl_validate"),
        ("infrahub_ctl.check", "infrahubctl check", "40_infrahubctl_check"),
    )
    print(f" - [{NAMESPACE}] Generate CLI documentation")
    for command in CLI_COMMANDS:
        exec_cmd = f'typer  {command[0]} utils docs --name "{command[1]}" --output docs/25_infrahubctl/{command[2]}.md'
        with context.cd(REPO_BASE):
            context.run(exec_cmd)


# ----------------------------------------------------------------------------
# Formatting tasks
# ----------------------------------------------------------------------------
@task
def format_black(context: Context):
    """Run black to format all Python files."""

    print(f" - [{NAMESPACE}] Format code with black")
    exec_cmd = f"black {MAIN_DIRECTORY}/"
    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def format_autoflake(context: Context):
    """Run autoflack to format all Python files."""

    print(f" - [{NAMESPACE}] Format code with autoflake")
    exec_cmd = f"autoflake --recursive --verbose --in-place --remove-all-unused-imports --remove-unused-variables {MAIN_DIRECTORY}"
    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def format_isort(context: Context):
    """Run isort to format all Python files."""

    print(f" - [{NAMESPACE}] Format code with isort")
    exec_cmd = f"isort {MAIN_DIRECTORY}"
    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task(name="format")
def format_all(context: Context):
    """This will run all formatter."""

    format_isort(context)
    format_autoflake(context)
    format_black(context)

    print(f" - [{NAMESPACE}] All formatters have been executed!")


# ----------------------------------------------------------------------------
# Testing tasks
# ----------------------------------------------------------------------------
@task
def black(context: Context, docker: bool = False):
    """Run black to check that Python files adherence to black standards."""

    print(f" - [{NAMESPACE}] Check code with black")
    exec_cmd = f"black --check --diff {MAIN_DIRECTORY}"

    if docker:
        compose_files_cmd = build_test_compose_files_cmd(database=False)
        exec_cmd = (
            f"{get_env_vars(context)} docker compose {compose_files_cmd} -p {BUILD_NAME} run infrahub-test {exec_cmd}"
        )
        print(exec_cmd)

    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def isort(context: Context, docker: bool = False):
    """Run isort to check that Python files adherence to import standards."""

    print(f" - [{NAMESPACE}] Check code with isort")
    exec_cmd = f"isort --check --diff {MAIN_DIRECTORY}"

    if docker:
        compose_files_cmd = build_test_compose_files_cmd(database=False)
        exec_cmd = (
            f"{get_env_vars(context)} docker compose {compose_files_cmd} -p {BUILD_NAME} run infrahub-test {exec_cmd}"
        )
        print(exec_cmd)

    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def mypy(context: Context, docker: bool = False):
    """This will run mypy for the specified name and Python version."""

    print(f" - [{NAMESPACE}] Check code with mypy")
    exec_cmd = f"mypy --show-error-codes {MAIN_DIRECTORY}"

    if docker:
        compose_files_cmd = build_test_compose_files_cmd(database=False)
        exec_cmd = (
            f"{get_env_vars(context)} docker compose {compose_files_cmd} -p {BUILD_NAME} run infrahub-test {exec_cmd}"
        )
        print(exec_cmd)

    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def pylint(context: Context, docker: bool = False):
    """This will run pylint for the specified name and Python version."""

    print(f" - [{NAMESPACE}] Check code with pylint")
    exec_cmd = f"pylint {MAIN_DIRECTORY}"

    if docker:
        compose_files_cmd = build_test_compose_files_cmd(database=False)
        exec_cmd = (
            f"{get_env_vars(context)} docker compose {compose_files_cmd} -p {BUILD_NAME} run infrahub-test {exec_cmd}"
        )
        print(exec_cmd)

    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def ruff(context: Context, docker: bool = False):
    """This will run ruff."""

    print(f" - [{NAMESPACE}] Check code with ruff")
    exec_cmd = f"ruff check {MAIN_DIRECTORY}"

    if docker:
        compose_files_cmd = build_test_compose_files_cmd(database=False)
        exec_cmd = (
            f"{get_env_vars(context)} docker compose {compose_files_cmd} -p {BUILD_NAME} run infrahub-test {exec_cmd}"
        )
        print(exec_cmd)

    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def lint(context: Context, docker: bool = False):
    """This will run all linter."""
    ruff(context, docker=docker)
    black(context, docker=docker)
    isort(context, docker=docker)
    pylint(context, docker=docker)
    mypy(context, docker=docker)

    print(f" - [{NAMESPACE}] All tests have passed!")


@task
def test_unit(context: Context):
    with context.cd(REPO_BASE):
        compose_files_cmd = build_test_compose_files_cmd(database=False)
        base_cmd = f"{get_env_vars(context)} docker compose {compose_files_cmd} -p {BUILD_NAME} run"
        exec_cmd = f"infrahub-test pytest -n {NBR_WORKERS} --dist loadscope -v --cov=infrahub_ctl {MAIN_DIRECTORY}/tests/unit"
        return execute_command(context=context, command=f"{base_cmd} {exec_cmd}")


# @task(optional=["database"])
# def test_integration(context: Context, database: str = "memgraph"):
#     with context.cd(REPO_BASE):
#         compose_files_cmd = build_test_compose_files_cmd(database=database)
#         base_cmd = f"{get_env_vars(context)} docker compose {compose_files_cmd} -p {BUILD_NAME} run"
#         exec_cmd = f"infrahub-test pytest -n {NBR_WORKERS} --dist loadscope -v --cov=infrahub_client {MAIN_DIRECTORY}/tests/integration"

#         return context.run(f"{base_cmd} {exec_cmd}")


@task(default=True)
def format_and_lint(context: Context):
    format_all(context)
    lint(context)

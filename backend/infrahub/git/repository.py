from __future__ import annotations

import glob
import hashlib
import importlib
import os
import shutil
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import git
import jinja2
import ujson
import yaml
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from pydantic import validator

import infrahub.config as config
from infrahub.checks import INFRAHUB_CHECK_VARIABLE_TO_IMPORT, InfrahubCheck
from infrahub.exceptions import (
    CheckError,
    CommitNotFoundError,
    Error,
    FileNotFound,
    RepositoryError,
    TransformError,
)
from infrahub.log import get_logger
from infrahub.transforms import INFRAHUB_TRANSFORM_VARIABLE_TO_IMPORT
from infrahub_client import GraphQLError, InfrahubClient, InfrahubNode, ValidationError
from infrahub_client.utils import compare_lists

# pylint: disable=too-few-public-methods,too-many-lines

LOGGER = get_logger("infrahub.git")

COMMITS_DIRECTORY_NAME = "commits"
BRANCHES_DIRECTORY_NAME = "branches"
TEMPORARY_DIRECTORY_NAME = "temp"


def get_repositories_directory() -> str:
    """Return the absolute path to the main directory used for the repositories."""
    repos_dir = config.SETTINGS.git.repositories_directory
    if not os.path.isabs(repos_dir):
        current_dir = os.getcwd()
        repos_dir = os.path.join(current_dir, config.SETTINGS.git.repositories_directory)

    return str(repos_dir)


def initialize_repositories_directory() -> bool:
    """Check if the main repositories_directory already exist, if not create it.

    Return
        True if the directory has been created,
        False if the directory was already present.
    """
    repos_dir = get_repositories_directory()
    if not os.path.isdir(repos_dir):
        os.makedirs(repos_dir)
        LOGGER.debug(f"Initialized the repositories_directory at {repos_dir}")
        return True

    LOGGER.debug(f"Repositories_directory already present at {repos_dir}")
    return False


class GraphQLQueryInformation(BaseModel):
    name: str
    """Name of the query"""

    filename: str
    """Name of the file. Example: myquery.gql"""

    query: str
    """Query in string format"""


class RFileInformation(BaseModel):
    name: str
    """Name of the RFile"""

    description: Optional[str]
    """Description of the RFile"""

    query: str
    """ID or name of the GraphQL Query associated with this RFile"""

    repository: str = "self"
    """ID of the associated repository or self"""

    template_path: str
    """Path to the template file within the repo"""


class ArtifactDefinitionInformation(BaseModel):
    name: str
    """Name of the Artifact Definition"""

    artifact_name: Optional[str]
    parameters: dict
    content_type: str
    targets: str
    transformation: str


class CheckDefinitionInformation(BaseModel):
    name: str
    """Name of the check"""

    repository: str = "self"
    """ID of the associated repository or self"""

    query: str
    """ID or name of the GraphQL Query associated with this Check"""

    file_path: str
    """Path to the python file within the repo"""

    class_name: str
    """Name of the Python Class"""

    check_class: Any
    """Python Class of the Check"""

    rebase: bool
    """Flag to indicate if the query need to be rebased."""

    timeout: int
    """Timeout for the Check."""

    targets: Optional[str] = None
    """ID or name of the Group associated with this CheckDefinition"""

    parameters: Optional[dict] = None
    """Additional Parameters to extract from each target (if targets is provided)"""


class TransformPythonInformation(BaseModel):
    name: str
    """Name of the Transform"""

    repository: str
    """ID or name of the repository this Transform is assocated with"""

    file_path: str
    """file_path of the TransformFunction within the repository"""

    query: str
    """ID or name of the GraphQLQuery this Transform is assocated with"""

    url: str
    """External URL for the Transform function"""

    class_name: str
    """Name of the Python Class of the Transform Function"""

    transform_class: Any
    """Python Class of the Transform"""

    rebase: bool
    """Flag to indicate if the query need to be rebased."""

    timeout: int
    """Timeout for the function."""


class RepoFileInformation(BaseModel):
    filename: str
    """Name of the file. Example: myfile.py"""

    filename_wo_ext: str
    """Name of the file, without the extension, Example: myfile """

    module_name: str
    """Name of the module for Python, in dot notation from the root of the repository, Example: commits.71da[..]4b7.checks.myfile """

    relative_path_dir: str
    """Relative path to the directory containing the file from the root of the worktree, Example: checks/"""

    relative_repo_path_dir: str
    """Relative path to the directory containing the file from the root of repository, Example: commits/71da[..]4b7/checks/"""

    absolute_path_dir: str
    """Absolute path to the directory containing the file, Example: /opt/infrahub/git/repo01/commits/71da[..]4b7/checks/"""

    relative_path_file: str
    """Relative path to the file from the root of the worktree Example: checks/myfile.py"""

    extension: str
    """Extension of the file Example: py """


class ArtifactGenerateResult(BaseModel):
    changed: bool
    checksum: str
    storage_id: str
    artifact_id: str


def extract_repo_file_information(
    full_filename: str, repo_directory: str, worktree_directory: Optional[str] = None
) -> RepoFileInformation:
    """Extract all the relevant and required information from a filename.

    Args:
        full_filename (str): Absolute path to the file to load Example:/opt/infrahub/git/repo01/commits/71da[..]4b7/myfile.py
        root_directory: Absolute path to the root of the repository directory. Example:/opt/infrahub/git/repo01
        worktree_directory (str, optional): Absolute path to the root of the worktree directory. Defaults to None. example: /opt/infrahub/git/repo01/commits/71da[..]4b7/

    Returns:
        RepoFileInformation: Pydantic object to store all information about this file
    """
    abs_directory_name = os.path.dirname(full_filename)
    filename = os.path.basename(full_filename)
    filename_wo_ext, extension = os.path.splitext(filename)

    relative_repo_path_dir = abs_directory_name.replace(repo_directory, "")
    if relative_repo_path_dir.startswith("/"):
        relative_repo_path_dir = relative_repo_path_dir[1:]

    if worktree_directory and worktree_directory in abs_directory_name:
        path_in_repo = abs_directory_name.replace(worktree_directory, "")
        if path_in_repo.startswith("/"):
            path_in_repo = path_in_repo[1:]
    else:
        path_in_repo = abs_directory_name

    file_path = os.path.join(path_in_repo, filename)

    module_name = relative_repo_path_dir.replace("/", ".") + f".{filename_wo_ext}"

    return RepoFileInformation(
        filename=filename,
        filename_wo_ext=filename_wo_ext,
        module_name=module_name,
        absolute_path_dir=abs_directory_name,
        relative_path_dir=path_in_repo,
        relative_repo_path_dir=relative_repo_path_dir,
        extension=extension,
        relative_path_file=file_path,
    )


class Worktree(BaseModel):
    identifier: str
    directory: str
    commit: str
    branch: Optional[str] = None

    @classmethod
    def init(cls, text):
        lines = text.split("\n")

        full_directory = lines[0].replace("worktree ", "")

        # Extract the identifier from the directory name
        # We first need to substract the main repository_directory to get the relative path.
        repo_directory = get_repositories_directory()
        relative_directory = full_directory.replace(repo_directory, "")
        relative_paths = relative_directory.split("/")

        identifier = None
        if len(relative_paths) == 3:
            # this is the main worktree for the main branch
            identifier = relative_paths[2]
        elif len(relative_paths) == 4:
            # this is the either a commit or a branch worktree
            identifier = relative_paths[3]
        else:
            raise Error("Unexpected directory path for a worktree.")

        item = cls(
            identifier=identifier,
            directory=full_directory,
            commit=lines[1].replace("HEAD ", ""),
        )

        if lines[2] != "detached":
            item.branch = lines[1].replace("branch refs/heads", "")

        return item


class BranchInGraph(BaseModel):
    id: str
    name: str
    is_data_only: bool
    commit: Optional[str]


class BranchInRemote(BaseModel):
    name: str
    commit: str


class BranchInLocal(BaseModel):
    name: str
    commit: str
    has_worktree: bool = False


class InfrahubRepository(BaseModel):  # pylint: disable=too-many-public-methods
    """
    Local version of a Git repository organized to work with Infrahub.
    The idea is that all commits that are being tracked in the graph will be checkout out
    individually as worktree under the <repo_name>/commits subdirectory

    Directory organization
    <repo_directory>/
        <repo_name>/main       Primary directory with the complete clone
        <repo_name>/branch     Directory for worktrees of all branches
        <repo_name>/commit     Directory for worktrees of individual commits
    """

    id: UUID
    name: str
    default_branch_name: Optional[str]
    type: Optional[str]
    location: Optional[str]
    has_origin: bool = False

    client: Optional[InfrahubClient]

    cache_repo: Optional[Repo]

    class Config:
        arbitrary_types_allowed = True

    # pylint: disable=no-self-argument
    @validator("default_branch_name", pre=True, always=True)
    def set_default_branch_name(cls, value):
        return value or config.SETTINGS.main.default_branch

    @property
    def directory_root(self) -> str:
        """Return the path to the root directory for this repository."""
        current_dir = os.getcwd()
        repositories_directory = config.SETTINGS.git.repositories_directory
        if not os.path.isabs(repositories_directory):
            repositories_directory = os.path.join(current_dir, config.SETTINGS.git.repositories_directory)

        return os.path.join(repositories_directory, self.name)

    @property
    def directory_default(self) -> str:
        """Return the path to the directory of the main branch."""
        return os.path.join(self.directory_root, config.SETTINGS.main.default_branch)

    @property
    def directory_branches(self) -> str:
        """Return the path to the directory where the worktrees of all the branches are stored."""
        return os.path.join(self.directory_root, BRANCHES_DIRECTORY_NAME)

    @property
    def directory_commits(self) -> str:
        """Return the path to the directory where the worktrees of all the commits are stored."""
        return os.path.join(self.directory_root, COMMITS_DIRECTORY_NAME)

    @property
    def directory_temp(self) -> str:
        """Return the path to the directory where the temp worktrees of all the commits pending validation are stored."""
        return os.path.join(self.directory_root, TEMPORARY_DIRECTORY_NAME)

    def get_git_repo_main(self) -> Repo:
        """Return Git Repo object of the main repository.

        Returns:
            Repo: git object of the main repository

        Raises:
            git.exc.InvalidGitRepositoryError if the default directory is not a valid Git repository.
        """

        if not self.cache_repo:
            self.cache_repo = Repo(self.directory_default)

        return self.cache_repo

    def get_git_repo_worktree(self, identifier: str) -> Repo:
        """Return Git Repo object of the given worktree.

        Returns:
            Repo: git object of the main repository

        """
        if worktree := self.get_worktree(identifier=identifier):
            return Repo(worktree.directory)

        return None

    def validate_local_directories(self) -> bool:
        """Check if the local directories structure to ensure that the repository has been properly initialized.

        Returns True if everything is correct
        Raises a RepositoryError exception if something is not correct
        """

        directories_to_validate = [
            self.directory_root,
            self.directory_branches,
            self.directory_commits,
            self.directory_temp,
            self.directory_default,
        ]

        for directory in directories_to_validate:
            if not os.path.isdir(directory):
                raise RepositoryError(
                    identifier=self.name,
                    message=f"Invalid file system for {self.name}, Local directory {directory} missing.",
                )

        # Validate that a worktree for the commit in main is present
        try:
            repo = self.get_git_repo_main()
            if "origin" in repo.remotes:
                self.has_origin = True

        except InvalidGitRepositoryError as exc:
            raise RepositoryError(
                identifier=self.name, message=f"The data on disk is not a valid Git repository for {self.name}."
            ) from exc

        # Validate that at least one worktree for the active commit in main has been created
        try:
            commit = str(repo.head.commit)
        except ValueError as exc:
            raise RepositoryError(
                identifier=self.name, message="The initial commit is missing for {self.name}"
            ) from exc

        if not os.path.isdir(os.path.join(self.directory_commits, commit)):
            raise RepositoryError(
                identifier=self.name, message=f"The directory for the main commit is missing for {self.name}"
            )

        return True

    async def create_locally(self) -> bool:
        """Ensure the required directory already exist in the filesystem or create them if needed.

        Returns
            True if the directory has been created,
            False if the directory was already present.
        """

        initialize_repositories_directory()

        if not self.location:
            raise RepositoryError(
                identifier=self.name,
                message=f"Unable to initialize the repository {self.name} without a remote location.",
            )

        # Check if the root, commits and branches directories are already present, create them if needed
        if os.path.isdir(self.directory_root):
            shutil.rmtree(self.directory_root)
            LOGGER.warning(f"Found an existing directory at {self.directory_root}, deleted it")
        elif os.path.isfile(self.directory_root):
            os.remove(self.directory_root)
            LOGGER.warning(f"Found an existing file at {self.directory_root}, deleted it")

        # Initialize directory structure
        os.makedirs(self.directory_root)
        os.makedirs(self.directory_branches)
        os.makedirs(self.directory_commits)
        os.makedirs(self.directory_temp)

        try:
            repo = Repo.clone_from(self.location, self.directory_default)
            repo.git.checkout(self.default_branch_name)
        except GitCommandError as exc:
            if "Repository not found" in exc.stderr or "does not appear to be a git" in exc.stderr:
                raise RepositoryError(
                    identifier=self.name,
                    message=f"Unable to clone the repository {self.name}, please check the address and the credential",
                ) from exc

            if "error: pathspec" in exc.stderr:
                raise RepositoryError(
                    identifier=self.name,
                    message=f"The branch {self.default_branch_name} isn't a valid branch for the repository {self.name} at {self.location}.",
                ) from exc

            raise RepositoryError(identifier=self.name) from exc

        self.has_origin = True

        # Create a worktree for the commit in main
        # TODO Need to handle the potential exceptions coming from repo.git.worktree
        commit = str(repo.head.commit)
        self.create_commit_worktree(commit=commit)
        await self.update_commit_value(branch_name=self.default_branch_name, commit=commit)

        return True

    @classmethod
    async def new(cls, **kwargs):
        self = cls(**kwargs)
        await self.create_locally()
        LOGGER.info(f"{self.name} | Created the new project locally.")
        return self

    @classmethod
    async def init(cls, **kwargs):
        self = cls(**kwargs)
        self.validate_local_directories()
        LOGGER.debug(f"{self.name} | Initiated the object on an existing directory.")
        return self

    def has_worktree(self, identifier: str) -> bool:
        """Return True if a worktree with a given identifier already exist."""

        worktrees = self.get_worktrees()

        for worktree in worktrees:
            if worktree.identifier == identifier:
                return True

        return False

    def get_worktree(self, identifier: str) -> Worktree:
        """Access a specific worktree by its identifier."""

        worktrees = self.get_worktrees()

        for worktree in worktrees:
            if worktree.identifier == identifier:
                return worktree

        return None

    def get_commit_worktree(self, commit: str) -> Worktree:
        """Access a specific commit worktree."""

        worktrees = self.get_worktrees()

        for worktree in worktrees:
            if worktree.identifier == commit:
                return worktree

        # if not worktree exist for this commit already
        # We'll try to create one
        return self.create_commit_worktree(commit=commit)

    def get_worktrees(self) -> List[Worktree]:
        """Return the list of worktrees configured for this repository."""
        repo = self.get_git_repo_main()
        responses = repo.git.worktree("list", "--porcelain").split("\n\n")

        return [Worktree.init(response) for response in responses]

    async def get_branches_from_graph(self) -> Dict[str, BranchInGraph]:
        """Return a dict with all the branches present in the graph.
        Query the list of branches first then query the repository for each branch.
        """

        response = {}

        branches = await self.client.branch.all()

        # TODO Need to optimize this query, right now we are querying everything unnecessarily
        repositories = await self.client.get_list_repositories(branches=branches)
        repository = repositories[self.name]

        for branch_name, branch in branches.items():
            response[branch_name] = BranchInGraph(
                id=branch.id,
                name=branch.name,
                is_data_only=branch.is_data_only,
                commit=repository.branches[branch_name] or None,
            )

        return response

    def get_branches_from_remote(self) -> Dict[str, BranchInRemote]:
        """Return a dict with all the branches present on the remote."""

        git_repo = self.get_git_repo_main()

        branches = {}

        for remote_branch in git_repo.remotes.origin.refs:
            if not isinstance(remote_branch, git.refs.remote.RemoteReference):  # pylint: disable=no-member
                continue

            short_name = remote_branch.name.replace("origin/", "")

            if short_name == "HEAD":
                continue

            branches[short_name] = BranchInRemote(name=short_name, commit=str(remote_branch.commit))

        return branches

    def get_branches_from_local(self, include_worktree: bool = True) -> Dict[str, BranchInLocal]:
        """Return a dict with all the branches present locally."""

        git_repo = self.get_git_repo_main()

        if include_worktree:
            worktrees = self.get_worktrees()

        branches = {}

        for local_branch in git_repo.refs:
            if local_branch.is_remote():
                continue

            has_worktree = False

            if include_worktree:
                for worktree in worktrees:
                    if worktree.branch and worktree.branch == local_branch.name:
                        has_worktree = True
                        break

            branches[local_branch.name] = BranchInLocal(
                name=local_branch.name, commit=str(local_branch.commit), has_worktree=has_worktree
            )

        return branches

    def get_commit_value(self, branch_name, remote: bool = False) -> str:
        branches = None
        if remote:
            branches = self.get_branches_from_remote()
        else:
            branches = self.get_branches_from_local(include_worktree=False)

        if branch_name not in branches:
            raise ValueError(f"Branch {branch_name} not found.")

        return str(branches[branch_name].commit)

    async def update_commit_value(self, branch_name: str, commit: str) -> bool:
        """Compare the value of the commit in the graph with the current commit on the filesystem.
        update it if they don't match.

        Returns:
            True if the commit has been updated
            False if they already had the same value
        """

        if not self.client:
            LOGGER.warning("Unable to update the value of the commit because a valid client hasn't been provided.")
            return

        LOGGER.debug(f"{self.name} | Updating commit value to {commit} for branch {branch_name}")
        await self.client.repository_update_commit(branch_name=branch_name, repository_id=self.id, commit=commit)

        return True

    async def create_branch_in_git(self, branch_name: str, push_origin: bool = True) -> bool:
        """Create new branch in the repository, assuming the branch has been created in the graph already."""

        repo = self.get_git_repo_main()

        # Check if the branch already exist locally, if it does do nothing
        local_branches = self.get_branches_from_local(include_worktree=False)
        if branch_name in local_branches:
            return False

        # TODO Catch potential exceptions coming from repo.git.branch & repo.git.worktree
        repo.git.branch(branch_name)
        self.create_branch_worktree(branch_name=branch_name)

        # If there is not remote configured, we are done
        #  Since the branch is a match for the main branch we don't need to create a commit worktree
        # If there is a remote, Check if there is an existing remote branch with the same name and if so track it.
        if not self.has_origin:
            LOGGER.debug("%s | Branch %s created in Git without tracking a remote branch.", self.name, branch_name)
            return True

        remote_branch = [br for br in repo.remotes.origin.refs if br.name == f"origin/{branch_name}"]

        if remote_branch:
            br_repo = self.get_git_repo_worktree(identifier=branch_name)
            br_repo.head.reference.set_tracking_branch(remote_branch[0])
            br_repo.remotes.origin.pull(branch_name)
            self.create_commit_worktree(str(br_repo.head.reference.commit))
            LOGGER.debug(
                "%s | Branch %s  created in Git, tracking remote branch %s.", self.name, branch_name, remote_branch[0]
            )
        else:
            LOGGER.debug(f"{self.name} | Branch {branch_name} created in Git without tracking a remote branch.")

        if push_origin:
            await self.push(branch_name)

        return True

    async def create_branch_in_graph(self, branch_name: str):
        """Create a new branch in the graph.

        NOTE We need to validate that we are not gonna end up with a race condition
        since a call to the GraphQL API will trigger a new RPC call to add a branch in this repo.
        """

        # TODO need to handle the exception properly
        await self.client.branch.create(branch_name=branch_name, background_execution=True)

        LOGGER.debug(f"{self.name} | Branch {branch_name} created in the Graph")
        return True

    def create_commit_worktree(self, commit: str) -> Union[bool, Worktree]:
        """Create a new worktree for a given commit."""

        # Check of the worktree already exist
        if self.has_worktree(identifier=commit):
            return False

        directory = os.path.join(self.directory_commits, commit)
        worktree = Worktree(identifier=commit, directory=str(directory), commit=commit)

        repo = self.get_git_repo_main()
        try:
            repo.git.worktree("add", directory, commit)
            LOGGER.debug(f"{self.name} | Commit worktree created {commit}")
            return worktree
        except GitCommandError as exc:
            if "invalid reference" in exc.stderr:
                raise CommitNotFoundError(
                    identifier=self.name,
                    commit=commit,
                ) from exc
            raise RepositoryError(identifier=self.name, message=exc.stderr) from exc

    def create_branch_worktree(self, branch_name: str) -> bool:
        """Create a new worktree for a given branch."""

        # Check if the worktree already exist
        if self.has_worktree(identifier=branch_name):
            return False

        try:
            repo = self.get_git_repo_main()
            repo.git.worktree("add", os.path.join(self.directory_branches, branch_name), branch_name)
        except GitCommandError as exc:
            raise RepositoryError(identifier=self.name, message=exc.stderr) from exc

        LOGGER.debug(f"{self.name} | Branch worktree created {branch_name}")
        return True

    async def calculate_diff_between_commits(
        self, first_commit: str, second_commit: str
    ) -> Tuple[List[str], List[str], List[str]]:
        """TODO need to refactor this function to return more information.
        Like :
          - What has changed inside the files
          - Are there some conflicts between the files.
        """

        git_repo = self.get_git_repo_main()

        commit_to_compare = git_repo.commit(second_commit)
        commit_in_branch = git_repo.commit(first_commit)

        changed_files = []
        removed_files = []
        added_files = []

        for x in commit_in_branch.diff(commit_to_compare, create_patch=True):
            if x.a_blob and not x.b_blob and x.a_blob.path not in added_files:
                added_files.append(x.a_blob.path)
            elif x.a_blob and x.b_blob and x.a_blob.path not in changed_files:
                changed_files.append(x.a_blob.path)
            elif not x.a_blob and x.b_blob and x.b_blob.path not in removed_files:
                removed_files.append(x.b_blob.path)

        return changed_files, added_files, removed_files

    async def push(self, branch_name: str) -> bool:
        """Push a given branch to the remote Origin repository"""

        if not self.has_origin:
            return False

        LOGGER.debug(f"{self.name} | Pushing the latest update to the remote origin for the branch '{branch_name}'")

        # TODO Catch potential exceptions coming from origin.push
        repo = self.get_git_repo_worktree(identifier=branch_name)
        repo.remotes.origin.push(branch_name)

        return True

    async def fetch(self) -> bool:
        """Fetch the latest update from the remote repository and bring a copy locally."""
        if not self.has_origin:
            return False

        LOGGER.debug(f"{self.name} | Fetching the latest updates from remote origin.")

        repo = self.get_git_repo_main()
        repo.remotes.origin.fetch()

        return True

    async def sync(self):
        """Synchronize the repository with its remote origin and with the database.

        By default the sync will focus only on the branches pulled from origin that have some differences with the local one.
        """

        LOGGER.info(f"{self.name} | Starting the synchronization.")

        await self.fetch()

        new_branches, updated_branches = await self.compare_local_remote()

        if not new_branches and not updated_branches:
            return True

        LOGGER.debug(f"{self.name} | New Branches {new_branches}, Updated Branches {updated_branches} ")

        # TODO need to handle properly the situation when a branch is not valid.
        for branch_name in new_branches:
            is_valid = await self.validate_remote_branch(branch_name=branch_name)
            if not is_valid:
                continue

            try:
                await self.create_branch_in_graph(branch_name=branch_name)
            except GraphQLError as exc:
                if "already exist" not in exc.errors[0]["message"]:
                    raise

            await self.create_branch_in_git(branch_name=branch_name)

            commit = self.get_commit_value(branch_name=branch_name, remote=False)
            self.create_commit_worktree(commit=commit)
            await self.update_commit_value(branch_name=branch_name, commit=commit)

            await self.import_objects_from_files(branch_name=branch_name, commit=commit)

        for branch_name in updated_branches:
            is_valid = await self.validate_remote_branch(branch_name=branch_name)
            if not is_valid:
                continue

            commit_after = await self.pull(branch_name=branch_name)
            await self.import_objects_from_files(branch_name=branch_name, commit=commit_after)

            if commit_after is True:
                LOGGER.warning(
                    f"{self.name} | An update was detected on {branch_name} but the commit remained the same after pull() ({commit_after}) ."
                )

        return True

    async def compare_local_remote(self) -> Tuple[List[str], List[str]]:
        """
        Returns:
            List[str] New Branches in Remote
            List[str] Branches with different commit in Remote
        """
        if not self.has_origin:
            return [], []

        # TODO move this section into a dedicated function to compare and bring in sync the remote repo with the local one.
        # It can be useful just after a clone etc ...
        local_branches = self.get_branches_from_local()
        remote_branches = self.get_branches_from_remote()

        new_branches = set(remote_branches.keys()) - set(local_branches.keys())
        existing_branches = set(local_branches.keys()) - new_branches

        updated_branches = []

        for branch_name in existing_branches:
            if (
                branch_name in remote_branches
                and branch_name in local_branches
                and remote_branches[branch_name].commit != local_branches[branch_name].commit
            ):
                LOGGER.info(f"New commit detected in branch {branch_name}")
                updated_branches.append(branch_name)

        return sorted(list(new_branches)), sorted(updated_branches)

    async def validate_remote_branch(self, branch_name: str) -> bool:  # pylint: disable=unused-argument
        """Validate a branch present on the remote repository.
        To check a branch we need to first create a worktree in the temporary folder then apply some checks:
        - xxx

        At the end, we need to delete the worktree in the temporary folder.
        """

        # Find the commit on the remote branch
        # Check out the commit in a worktree
        # Validate

        return True

    async def pull(self, branch_name: str) -> Union[bool, str]:
        """Pull the latest update from the remote repository on a given branch."""

        if not self.has_origin:
            return False

        repo = self.get_git_repo_worktree(identifier=branch_name)
        if not repo:
            raise ValueError(f"Unable to identify the worktree for the branch : {branch_name}")

        try:
            commit_before = str(repo.head.commit)
            repo.remotes.origin.pull(branch_name)
        except GitCommandError as exc:
            if "Need to specify how to reconcile" in exc.stderr:
                raise RepositoryError(
                    identifier=self.name,
                    message=f"Unable to pull the branch {branch_name} for repository {self.name}, there is a conflict that must be resolved.",
                ) from exc
            raise RepositoryError(identifier=self.name, message=exc.stderr) from exc

        commit_after = str(repo.head.commit)

        if commit_after == commit_before:
            return True

        self.create_commit_worktree(commit=commit_after)
        await self.update_commit_value(branch_name=branch_name, commit=commit_after)

        return commit_after

    async def merge(self, source_branch: str, dest_branch: str, push_remote: bool = True) -> bool:
        """Merge the source branch into the destination branch.

        After the rebase we need to resync the data
        """
        repo = self.get_git_repo_worktree(identifier=dest_branch)
        if not repo:
            raise ValueError(f"Unable to identify the worktree for the branch : {dest_branch}")

        commit_before = str(repo.head.commit)
        commit = self.get_commit_value(branch_name=source_branch, remote=False)

        try:
            repo.git.merge(commit)
        except GitCommandError as exc:
            raise RepositoryError(identifier=self.name, message=exc.stderr) from exc

        commit_after = str(repo.head.commit)

        if commit_after == commit_before:
            return False

        self.create_commit_worktree(commit_after)
        await self.update_commit_value(branch_name=dest_branch, commit=commit_after)

        if self.has_origin and push_remote:
            await self.push(branch_name=dest_branch)

        return str(commit_after)

    async def rebase(self, branch_name: str, source_branch: str = "main", push_remote: bool = True) -> bool:
        """Rebase the current branch with main.

        Technically we are not doing a Git rebase because it will change the git history
        We'll merge the content of the source_branch into branch_name instead to keep the history clear.

        TODO need to see how we manage conflict

        After the rebase we need to resync the data
        """

        response = await self.merge(dest_branch=branch_name, source_branch=source_branch, push_remote=push_remote)

        return response

    async def import_objects_from_files(self, branch_name: str, commit: Optional[str] = None):
        if not self.client:
            LOGGER.warning("Unable to import the objects from the files because a valid client hasn't been provided.")
            return

        if not commit:
            commit = self.get_commit_value(branch_name=branch_name)

        await self.import_all_graphql_query(branch_name=branch_name, commit=commit)
        await self.import_all_python_files(branch_name=branch_name, commit=commit)
        await self.import_all_yaml_files(branch_name=branch_name, commit=commit)

    async def import_objects_rfiles(self, branch_name: str, commit: str, data: List[dict]):
        LOGGER.debug(f"{self.name} | Importing all RFiles in branch {branch_name} ({commit}) ")

        schema = await self.client.schema.get(kind="CoreRFile", branch=branch_name)

        rfiles_in_graph = {
            rfile.name.value: rfile
            for rfile in await self.client.filters(kind="CoreRFile", branch=branch_name, repository__ids=[str(self.id)])
        }

        local_rfiles = {}

        # Process the list of local RFile to organize them by name
        for rfile in data:
            try:
                item = RFileInformation(**rfile)
                self.client.schema.validate_data_against_schema(schema=schema, data=rfile)
            except PydanticValidationError as exc:
                for error in exc.errors():
                    LOGGER.error(f"  {'/'.join(error['loc'])} | {error['msg']} ({error['type']})")
                continue
            except ValidationError as exc:
                LOGGER.error(exc.message)
                continue

            # Insert the ID of the current repository if required
            if item.repository == "self":
                item.repository = self.id

            # Query the GraphQL query and (eventually) replace the name with the ID
            graphql_query = await self.client.get(
                kind="CoreGraphQLQuery", branch=branch_name, id=str(item.query), populate_store=True
            )
            item.query = graphql_query.id

            local_rfiles[item.name] = item

        present_in_both, only_graph, only_local = compare_lists(
            list1=list(rfiles_in_graph.keys()), list2=list(local_rfiles.keys())
        )

        for rfile_name in only_local:
            LOGGER.info(f"{self.name}: New RFile {rfile_name!r} found on branch {branch_name!r}, creating")
            await self.create_rfile(branch_name=branch_name, data=local_rfiles[rfile_name])

        for rfile_name in present_in_both:
            if not await self.compare_rfile(
                existing_rfile=rfiles_in_graph[rfile_name], local_rfile=local_rfiles[rfile_name]
            ):
                LOGGER.info(
                    f"{self.name} | New version of the RFile '{rfile_name}' found on branch {branch_name}, updating"
                )
                await self.update_rfile(
                    existing_rfile=rfiles_in_graph[rfile_name], local_rfile=local_rfiles[rfile_name]
                )

        for rfile_name in only_graph:
            LOGGER.info(f"{self.name} | RFile '{rfile_name}' not found locally in branch {branch_name}, deleting")
            await rfiles_in_graph[rfile_name].delete()

    async def create_rfile(self, branch_name: str, data: RFileInformation) -> InfrahubNode:
        schema = await self.client.schema.get(kind="CoreRFile", branch=branch_name)
        create_payload = self.client.schema.generate_payload_create(
            schema=schema, data=data.dict(), source=self.id, is_protected=True
        )
        obj = await self.client.create(kind="CoreRFile", branch=branch_name, **create_payload)
        await obj.save()
        return obj

    @classmethod
    async def compare_rfile(cls, existing_rfile: InfrahubNode, local_rfile: RFileInformation) -> bool:
        # pylint: disable=no-member
        if (
            existing_rfile.description.value != local_rfile.description
            or existing_rfile.template_path.value != local_rfile.template_path
            or existing_rfile.query.id != local_rfile.query
        ):
            return False

        return True

    async def update_rfile(self, existing_rfile: InfrahubNode, local_rfile: RFileInformation) -> None:
        # pylint: disable=no-member
        if existing_rfile.description.value != local_rfile.description:
            existing_rfile.description.value = local_rfile.description

        if existing_rfile.query.id != local_rfile.query:
            existing_rfile.query = {"id": local_rfile.query, "source": str(self.id), "is_protected": True}

        if existing_rfile.template_path.value != local_rfile.template_path:
            existing_rfile.template_path.value = local_rfile.template_path

        await existing_rfile.save()

    async def import_objects_artifact_definitions(self, branch_name: str, commit: str, data: List[dict]):
        LOGGER.debug(f"{self.name} | Importing all Artifact Definitions in branch {branch_name} ({commit}) ")

        schema = await self.client.schema.get(kind="CoreArtifactDefinition", branch=branch_name)

        artifact_defs_in_graph = {
            artdef.name.value: artdef
            for artdef in await self.client.filters(kind="CoreArtifactDefinition", branch=branch_name)
        }

        local_artifact_defs = {}

        # Process the list of local RFile to organize them by name
        for artdef in data:
            try:
                item = ArtifactDefinitionInformation(**artdef)
                self.client.schema.validate_data_against_schema(schema=schema, data=artdef)
            except PydanticValidationError as exc:
                for error in exc.errors():
                    LOGGER.error(f"  {'/'.join(error['loc'])} | {error['msg']} ({error['type']})")
                continue
            except ValidationError as exc:
                LOGGER.error(exc.message)
                continue

            local_artifact_defs[item.name] = item

        present_in_both, _, only_local = compare_lists(
            list1=list(artifact_defs_in_graph.keys()), list2=list(local_artifact_defs.keys())
        )

        for artdef_name in only_local:
            LOGGER.info(
                f"{self.name} | New Artifact Definition {artdef_name!r} found on branch {branch_name!r}, creating"
            )
            await self.create_artifact_definition(branch_name=branch_name, data=local_artifact_defs[artdef_name])

        for artdef_name in present_in_both:
            if not await self.compare_artifact_definition(
                existing_artifact_definition=artifact_defs_in_graph[artdef_name],
                local_artifact_definition=local_artifact_defs[artdef_name],
            ):
                LOGGER.info(
                    f"{self.name} | New version of the Artifact Definition '{artdef_name}' found on branch {branch_name}, updating"
                )
                await self.update_artifact_definition(
                    existing_artifact_definition=artifact_defs_in_graph[artdef_name],
                    local_artifact_definition=local_artifact_defs[artdef_name],
                )

    async def create_artifact_definition(self, branch_name: str, data: ArtifactDefinitionInformation) -> InfrahubNode:
        schema = await self.client.schema.get(kind="CoreArtifactDefinition", branch=branch_name)
        create_payload = self.client.schema.generate_payload_create(
            schema=schema, data=data.dict(), source=self.id, is_protected=True
        )
        obj = await self.client.create(kind="CoreArtifactDefinition", branch=branch_name, **create_payload)
        await obj.save()
        return obj

    @classmethod
    async def compare_artifact_definition(
        cls, existing_artifact_definition: InfrahubNode, local_artifact_definition: RFileInformation
    ) -> bool:
        # pylint: disable=no-member
        if (
            existing_artifact_definition.artifact_name.value != local_artifact_definition.artifact_name
            or existing_artifact_definition.parameters.value != local_artifact_definition.parameters
            or existing_artifact_definition.content_type.value != local_artifact_definition.content_type
        ):
            return False

    async def update_artifact_definition(
        self, existing_artifact_definition: InfrahubNode, local_artifact_definition: RFileInformation
    ) -> None:
        # pylint: disable=no-member
        if existing_artifact_definition.artifact_name.value != local_artifact_definition.artifact_name:
            existing_artifact_definition.artifact_name.value = local_artifact_definition.artifact_name

        if existing_artifact_definition.parameters.value != local_artifact_definition.parameters:
            existing_artifact_definition.parameters.value = local_artifact_definition.parameters

        if existing_artifact_definition.content_type.value != local_artifact_definition.content_type:
            existing_artifact_definition.content_type.value = local_artifact_definition.content_type

        await existing_artifact_definition.save()

    async def import_all_graphql_query(self, branch_name: str, commit: str) -> None:
        """Search for all .gql file and import them as GraphQL query."""

        LOGGER.debug(f"{self.name} | Importing all GraphQL Queries in branch {branch_name}")

        local_queries = {query.name: query for query in await self.find_graphql_queries(commit=commit)}
        if not local_queries:
            return

        queries_in_graph = {
            query.name.value: query
            for query in await self.client.filters(
                kind="CoreGraphQLQuery", branch=branch_name, repository__ids=[str(self.id)]
            )
        }

        present_in_both, only_graph, only_local = compare_lists(
            list1=list(queries_in_graph.keys()), list2=list(local_queries.keys())
        )

        for query_name in only_local:
            query = local_queries[query_name]
            LOGGER.info(f"{self.name} | New Graphql Query '{query_name}' found on branch {branch_name}, creating")
            await self.create_graphql_query(branch_name=branch_name, name=query_name, query_string=query.query)

        for query_name in present_in_both:
            local_query = local_queries[query_name]
            graph_query = queries_in_graph[query_name]
            if local_query.query != graph_query.query.value:
                LOGGER.info(
                    f"{self.name} | New version of the Graphql Query '{query_name}' found on branch {branch_name}, updating"
                )
                graph_query.query.value = local_query.query
                await graph_query.save()

        for query_name in only_graph:
            graph_query = queries_in_graph[query_name]
            LOGGER.info(
                f"{self.name} | Graphql Query '{query_name}' not found locally in branch {branch_name}, deleting"
            )
            await graph_query.delete()

    async def create_graphql_query(self, branch_name: str, name: str, query_string: str) -> InfrahubNode:
        data = {"name": name, "query": query_string, "repository": self.id}

        schema = await self.client.schema.get(kind="CoreGraphQLQuery", branch=branch_name)
        create_payload = self.client.schema.generate_payload_create(
            schema=schema,
            data=data,
            source=self.id,
            is_protected=True,
        )
        obj = await self.client.create(kind="CoreGraphQLQuery", branch=branch_name, **create_payload)
        await obj.save()
        return obj

    async def import_python_check_definitions_from_module(
        self, branch_name: str, commit: str, module: types.ModuleType, file_path: str
    ) -> None:
        if INFRAHUB_CHECK_VARIABLE_TO_IMPORT not in dir(module):
            return False

        checks_definition_in_graph = {
            check.name.value: check
            for check in await self.client.filters(
                kind="CoreCheckDefinition", branch=branch_name, repository__ids=[str(self.id)]
            )
        }

        local_check_definitions = {}
        for check_class in getattr(module, INFRAHUB_CHECK_VARIABLE_TO_IMPORT):
            graphql_query = await self.client.get(
                kind="CoreGraphQLQuery", branch=branch_name, id=str(check_class.query), populate_store=True
            )
            try:
                item = CheckDefinitionInformation(
                    name=check_class.__name__,
                    repository=str(self.id),
                    class_name=check_class.__name__,
                    check_class=check_class,
                    file_path=file_path,
                    query=str(graphql_query.id),
                    timeout=check_class.timeout,
                    rebase=check_class.rebase,
                )
                local_check_definitions[item.name] = item
            except Exception as exc:  # pylint: disable=broad-exception-caught
                LOGGER.error(
                    f"{self.name} | An error occured while processing the CheckDefinition {check_class.__name__} from {file_path} : {exc} "
                )
                continue

        present_in_both, only_graph, only_local = compare_lists(
            list1=list(checks_definition_in_graph.keys()), list2=list(local_check_definitions.keys())
        )

        for check_name in only_local:
            LOGGER.info(
                f"{self.name} | New CheckDefinition '{check_name}' found on branch {branch_name} ({commit[:8]}), creating"
            )
            await self.create_python_check_definition(
                branch_name=branch_name, check=local_check_definitions[check_name]
            )

        for check_name in present_in_both:
            if not await self.compare_python_check_definition(
                check=local_check_definitions[check_name],
                existing_check=checks_definition_in_graph[check_name],
            ):
                LOGGER.info(
                    f"{self.name} | New version of CheckDefinition '{check_name}' found on branch {branch_name} ({commit[:8]}), updating"
                )
                await self.update_python_check_definition(
                    check=local_check_definitions[check_name],
                    existing_check=checks_definition_in_graph[check_name],
                )

        for check_name in only_graph:
            LOGGER.info(
                f"{self.name} | CheckDefinition '{check_name}' not found locally in branch {branch_name}, deleting"
            )
            await checks_definition_in_graph[check_name].delete()

    async def create_python_check_definition(self, branch_name: str, check: CheckDefinitionInformation) -> InfrahubNode:
        data = {
            "name": check.name,
            "repository": check.repository,
            "query": check.query,
            "file_path": check.file_path,
            "class_name": check.class_name,
            "rebase": check.rebase,
            "timeout": check.timeout,
            "targets": check.targets,
            "parameters": check.parameters,
        }

        schema = await self.client.schema.get(kind="CoreCheckDefinition", branch=branch_name)

        create_payload = self.client.schema.generate_payload_create(
            schema=schema,
            data=data,
            source=self.id,
            is_protected=True,
        )
        obj = await self.client.create(kind="CoreCheckDefinition", branch=branch_name, **create_payload)
        await obj.save()

        return obj

    async def update_python_check_definition(
        self,
        check: CheckDefinitionInformation,
        existing_check: InfrahubNode,
    ) -> None:
        if existing_check.query.id != check.query:
            existing_check.query = {"id": check.query, "source": str(self.id), "is_protected": True}

        if existing_check.file_path.value != check.file_path:
            existing_check.file_path.value = check.file_path

        if existing_check.rebase.value != check.rebase:
            existing_check.rebase.value = check.rebase

        if existing_check.timeout.value != check.timeout:
            existing_check.timeout.value = check.timeout

        if existing_check.targets.id != check.targets:
            existing_check.targets = {"id": check.targets, "source": str(self.id), "is_protected": True}

        if existing_check.parameters.value != check.parameters:
            existing_check.parameters.value = check.parameters

        await existing_check.save()

    @classmethod
    async def compare_python_check_definition(
        cls, check: CheckDefinitionInformation, existing_check: InfrahubNode
    ) -> bool:
        """Compare an existing Python Check Object with a Check Class
        and identify if we need to update the object in the database."""
        # pylint: disable=too-many-boolean-expressions
        if (
            existing_check.query.id != check.query
            or existing_check.file_path.value != check.file_path
            or existing_check.timeout.value != check.timeout
            or existing_check.rebase.value != check.rebase
            or existing_check.class_name.value != check.class_name
            or existing_check.parameters.value != check.parameters
        ):
            return False
        return True

    async def import_python_transforms_from_module(self, branch_name: str, commit: str, module, file_path: str):
        # TODO add function to validate if a check is valid

        if INFRAHUB_TRANSFORM_VARIABLE_TO_IMPORT not in dir(module):
            return False

        transforms_in_graph = {
            transform.name.value: transform
            for transform in await self.client.filters(
                kind="CoreTransformPython", branch=branch_name, repository__ids=[str(self.id)]
            )
        }

        local_transforms = {}

        for transform_class in getattr(module, INFRAHUB_TRANSFORM_VARIABLE_TO_IMPORT):
            transform = transform_class()

            # Query the GraphQL query and (eventually) replace the name with the ID
            graphql_query = await self.client.get(
                kind="CoreGraphQLQuery", branch=branch_name, id=str(transform.query), populate_store=True
            )

            item = TransformPythonInformation(
                name=transform.name,
                repository=str(self.id),
                query=str(graphql_query.id),
                file_path=file_path,
                url=transform.url,
                transform_class=transform,
                class_name=transform_class.__name__,
                rebase=transform.rebase,
                timeout=transform.timeout,
            )
            local_transforms[item.name] = item

        present_in_both, only_graph, only_local = compare_lists(
            list1=list(transforms_in_graph.keys()), list2=list(local_transforms.keys())
        )

        for transform_name in only_local:
            LOGGER.info(
                f"{self.name} | New Python Transform '{transform_name}' found on branch {branch_name} ({commit[:8]}), creating"
            )
            await self.create_python_transform(branch_name=branch_name, transform=local_transforms[transform_name])

        for transform_name in present_in_both:
            if not await self.compare_python_transform(
                existing_transform=transforms_in_graph[transform_name], local_transform=local_transforms[transform_name]
            ):
                LOGGER.info(
                    f"{self.name} | New version of the Python Transform '{transform_name}' found on branch {branch_name} ({commit[:8]}), updating"
                )
                await self.update_python_transform(
                    existing_transform=transforms_in_graph[transform_name],
                    local_transform=local_transforms[transform_name],
                )

        for transform_name in only_graph:
            LOGGER.info(
                f"{self.name} | Python Transform '{transform_name}' not found locally in branch {branch_name} ({commit[:8]}), deleting"
            )
            await transforms_in_graph[transform_name].delete()

    async def create_python_transform(self, branch_name: str, transform: TransformPythonInformation) -> InfrahubNode:
        schema = await self.client.schema.get(kind="CoreTransformPython", branch=branch_name)
        data = {
            "name": transform.name,
            "repository": transform.repository,
            "query": transform.query,
            "file_path": transform.file_path,
            "url": transform.url,
            "class_name": transform.class_name,
            "rebase": transform.rebase,
            "timeout": transform.timeout,
        }
        create_payload = self.client.schema.generate_payload_create(
            schema=schema,
            data=data,
            source=self.id,
            is_protected=True,
        )
        obj = await self.client.create(kind="CoreTransformPython", branch=branch_name, **create_payload)
        await obj.save()
        return obj

    async def update_python_transform(
        self, existing_transform: InfrahubNode, local_transform: TransformPythonInformation
    ) -> bool:
        if existing_transform.query.id != local_transform.query:
            existing_transform.query = {"id": local_transform.query, "source": str(self.id), "is_protected": True}

        if existing_transform.file_path.value != local_transform.file_path:
            existing_transform.file_path.value = local_transform.file_path

        if existing_transform.timeout.value != local_transform.timeout:
            existing_transform.timeout.value = local_transform.timeout

        if existing_transform.url.value != local_transform.url:
            existing_transform.url.value = local_transform.url

        if existing_transform.rebase.value != local_transform.rebase:
            existing_transform.rebase.value = local_transform.rebase

        await existing_transform.save()

    @classmethod
    async def compare_python_transform(
        cls, existing_transform: InfrahubNode, local_transform: TransformPythonInformation
    ) -> bool:
        if (
            existing_transform.query.id != local_transform.query
            or existing_transform.file_path.value != local_transform.file_path
            or existing_transform.timeout.value != local_transform.timeout
            or existing_transform.url.value != local_transform.url
            or existing_transform.rebase.value != local_transform.rebase
        ):
            return False
        return True

    async def import_all_yaml_files(self, branch_name: str, commit: str):
        yaml_files = await self.find_files(extension=["yml", "yaml"], commit=commit)

        for yaml_file in yaml_files:
            LOGGER.debug(f"{self.name} | Checking {yaml_file}")

            # ------------------------------------------------------
            # Import Yaml
            # ------------------------------------------------------
            with open(yaml_file, "r", encoding="UTF-8") as file_data:
                yaml_data = file_data.read()

            try:
                data = yaml.safe_load(yaml_data)
            except yaml.YAMLError as exc:
                LOGGER.warning(f"{self.name} | Unable to load YAML file {yaml_file} : {exc}")
                continue

            if not isinstance(data, dict):
                LOGGER.debug(f"{self.name} | {yaml_file} : payload is not a dictionnary .. SKIPPING")
                continue

            # ------------------------------------------------------
            # Search for Valid object types
            # ------------------------------------------------------
            for key, data in data.items():
                if not hasattr(self, f"import_objects_{key}"):
                    continue

                method = getattr(self, f"import_objects_{key}")
                await method(branch_name=branch_name, commit=commit, data=data)

    async def import_all_python_files(self, branch_name: str, commit: str):
        commit_wt = self.get_worktree(identifier=commit)

        python_files = await self.find_files(extension=["py"], commit=commit)

        # Ensure the path for this repository is present in sys.path
        if self.directory_root not in sys.path:
            sys.path.append(self.directory_root)

        for python_file in python_files:
            LOGGER.debug(f"{self.name} | Checking {python_file}")

            file_info = extract_repo_file_information(
                full_filename=python_file, repo_directory=self.directory_root, worktree_directory=commit_wt.directory
            )

            try:
                module = importlib.import_module(file_info.module_name)
            except ModuleNotFoundError:
                LOGGER.warning(f"{self.name} | Unable to load python file {python_file}")
                continue

            await self.import_python_check_definitions_from_module(
                branch_name=branch_name, commit=commit, module=module, file_path=file_info.relative_path_file
            )
            await self.import_python_transforms_from_module(
                branch_name=branch_name, commit=commit, module=module, file_path=file_info.relative_path_file
            )

    async def find_files(
        self,
        extension: Union[str, List[str]],
        branch_name: Optional[str] = None,
        commit: Optional[str] = None,
        recursive: bool = True,
    ) -> List[str]:
        """Return the absolute path of all files matching a specific extension in a given Branch or Commit."""
        if not branch_name and not commit:
            raise ValueError("Either branch_name or commit must be provided.")
        branch_wt = self.get_worktree(identifier=commit or branch_name)

        files = []

        if isinstance(extension, str):
            files.extend(glob.glob(f"{branch_wt.directory}/**/*.{extension}", recursive=recursive))
            files.extend(glob.glob(f"{branch_wt.directory}/**/.*.{extension}", recursive=recursive))
        elif isinstance(extension, list):
            for ext in extension:
                files.extend(glob.glob(f"{branch_wt.directory}/**/*.{ext}", recursive=recursive))
                files.extend(glob.glob(f"{branch_wt.directory}/**/.*.{ext}", recursive=recursive))
        return files

    async def find_graphql_queries(self, commit: str) -> List[GraphQLQueryInformation]:
        """Return the information about all GraphQL Queries present in a specific commit."""
        queries: List[GraphQLQueryInformation] = []
        query_files = await self.find_files(extension=["gql"], commit=commit)

        for query_file in query_files:
            filename = os.path.basename(query_file)
            name = os.path.splitext(filename)[0]

            queries.append(
                GraphQLQueryInformation(
                    name=name,
                    filename=filename,
                    query=Path(query_file).read_text(encoding="UTF-8"),
                )
            )
        return queries

    async def get_file(self, commit: str, location: str) -> str:
        commit_worktree = self.get_commit_worktree(commit=commit)

        self.validate_location(commit=commit, worktree_directory=commit_worktree.directory, file_path=location)

        full_filename = os.path.join(commit_worktree.directory, location)

        with open(full_filename, "r", encoding="UTF-8") as obj:
            content = obj.read()

        return content

    async def render_jinja2_template(self, commit: str, location: str, data: dict):
        commit_worktree = self.get_commit_worktree(commit=commit)

        self.validate_location(commit=commit, worktree_directory=commit_worktree.directory, file_path=location)

        try:
            templateLoader = jinja2.FileSystemLoader(searchpath=commit_worktree.directory)
            templateEnv = jinja2.Environment(loader=templateLoader, trim_blocks=True, lstrip_blocks=True)
            template = templateEnv.get_template(location)
            return template.render(**data)
        except Exception as exc:
            LOGGER.critical(exc, exc_info=True)
            raise TransformError(repository_name=self.name, commit=commit, location=location, message=str(exc)) from exc

    async def execute_python_check(
        self, branch_name: str, commit: str, location: str, class_name: str, client: InfrahubClient
    ) -> InfrahubCheck:
        """Execute A Python Check stored in the repository."""

        commit_worktree = self.get_commit_worktree(commit=commit)

        self.validate_location(commit=commit, worktree_directory=commit_worktree.directory, file_path=location)

        # Ensure the path for this repository is present in sys.path
        if self.directory_root not in sys.path:
            sys.path.append(self.directory_root)

        try:
            file_info = extract_repo_file_information(
                full_filename=os.path.join(commit_worktree.directory, location),
                repo_directory=self.directory_root,
                worktree_directory=commit_worktree.directory,
            )

            module = importlib.import_module(file_info.module_name)

            check_class = getattr(module, class_name)

            check = await check_class.init(root_directory=commit_worktree.directory, branch=branch_name, client=client)
            await check.run()

            return check

        except ModuleNotFoundError as exc:
            error_msg = f"Unable to load the check file {location} ({commit})"
            LOGGER.error(f"{self.name} | {error_msg}")
            raise CheckError(
                repository_name=self.name, class_name=class_name, commit=commit, location=location, message=error_msg
            ) from exc

        except AttributeError as exc:
            error_msg = f"Unable to find the class {class_name} in {location} ({commit})"
            LOGGER.error(f"{self.name} | {error_msg}")
            raise CheckError(
                repository_name=self.name, class_name=class_name, commit=commit, location=location, message=error_msg
            ) from exc

        except Exception as exc:
            LOGGER.critical(exc, exc_info=True)
            raise CheckError(
                repository_name=self.name, class_name=class_name, commit=commit, location=location, message=str(exc)
            ) from exc

    async def execute_python_transform(
        self, branch_name: str, commit: str, location: str, client: InfrahubClient, data: Optional[dict] = None
    ) -> Any:
        """Execute A Python Transform stored in the repository."""

        if "::" not in location:
            raise ValueError("Transformation location not valid, it must contains a double colons (::)")

        file_path, class_name = location.split("::")
        commit_worktree = self.get_commit_worktree(commit=commit)

        LOGGER.debug(f"Will run Python Transform from {class_name} at {location} ({commit})")

        self.validate_location(commit=commit, worktree_directory=commit_worktree.directory, file_path=file_path)

        # Ensure the path for this repository is present in sys.path
        if self.directory_root not in sys.path:
            sys.path.append(self.directory_root)

        try:
            file_info = extract_repo_file_information(
                full_filename=os.path.join(commit_worktree.directory, file_path),
                repo_directory=self.directory_root,
                worktree_directory=commit_worktree.directory,
            )

            module = importlib.import_module(file_info.module_name)

            transform_class = getattr(module, class_name)

            transform = await transform_class.init(
                root_directory=commit_worktree.directory, branch=branch_name, client=client
            )
            return await transform.run(data=data)

        except ModuleNotFoundError as exc:
            error_msg = f"Unable to load the transform file {location} ({commit})"
            LOGGER.error(f"{self.name} | {error_msg}")
            raise TransformError(
                repository_name=self.name, commit=commit, location=location, message=error_msg
            ) from exc

        except AttributeError as exc:
            error_msg = f"Unable to find the class {class_name} in {location} ({commit})"
            LOGGER.error(f"{self.name} | {error_msg}")
            raise TransformError(
                repository_name=self.name, commit=commit, location=location, message=error_msg
            ) from exc

        except Exception as exc:
            LOGGER.critical(exc, exc_info=True)
            raise TransformError(repository_name=self.name, commit=commit, location=location, message=str(exc)) from exc

    async def artifact_generate(
        self,
        branch_name: str,
        commit: str,
        artifact: InfrahubNode,
        target: InfrahubNode,
        definition: InfrahubNode,
        transformation: InfrahubNode,
        query: InfrahubNode,
    ) -> ArtifactGenerateResult:
        variables = target.extract(params=definition.parameters.value)
        data = await self.client.execute_graphql(
            query=query.query.value,
            variables=variables,
            tracker="artifact-query-graphql-data",
            branch_name=branch_name,
            rebase=transformation.rebase.value,
            timeout=transformation.timeout.value,
        )

        if transformation.typename == "CoreRFile":
            artifact_content = await self.render_jinja2_template(
                commit=commit, location=transformation.template_path.value, data={"data": data}
            )
        elif transformation.typename == "CoreTransformPython":
            transformation_location = f"{transformation.file_path.value}::{transformation.class_name.value}"
            artifact_content = await self.execute_python_transform(
                branch_name=branch_name, commit=commit, location=transformation_location, data=data, client=self.client
            )

        if definition.content_type.value == "application/json":
            artifact_content_str = ujson.dumps(artifact_content, indent=2)
        elif definition.content_type.value == "text/plain":
            artifact_content_str = artifact_content

        checksum = hashlib.md5(bytes(artifact_content_str, encoding="utf-8")).hexdigest()

        if artifact.checksum.value == checksum:
            return ArtifactGenerateResult(
                changed=False, checksum=checksum, storage_id=artifact.storage_id.value, artifact_id=artifact.id
            )

        resp = await self.client.object_store.upload(content=artifact_content_str, tracker="artifact-upload-content")
        storage_id = resp["identifier"]

        artifact.checksum.value = checksum
        artifact.storage_id.value = storage_id
        artifact.status.value = "Ready"
        await artifact.save()

        return ArtifactGenerateResult(changed=True, checksum=checksum, storage_id=storage_id, artifact_id=artifact.id)

    def validate_location(self, commit: str, worktree_directory: str, file_path: str) -> None:
        if not os.path.exists(os.path.join(worktree_directory, file_path)):
            raise FileNotFound(repository_name=self.name, commit=commit, location=file_path)

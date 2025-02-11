import logging
from pathlib import Path
from typing import Sequence
from mcp.server import Server
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
from mcp.types import (
    ClientCapabilities,
    TextContent,
    Tool,
    ListRootsResult,
    RootsCapability,
)
from enum import Enum
import git
from pydantic import BaseModel

class GitStatus(BaseModel):
    repo_path: str

class GitDiffUnstaged(BaseModel):
    repo_path: str

class GitDiffStaged(BaseModel):
    repo_path: str

class GitDiff(BaseModel):
    repo_path: str
    target: str

class GitCommit(BaseModel):
    repo_path: str
    message: str

class GitAdd(BaseModel):
    repo_path: str
    files: list[str]

class GitReset(BaseModel):
    repo_path: str

class GitLog(BaseModel):
    repo_path: str
    max_count: int = 10

class GitCreateBranch(BaseModel):
    repo_path: str
    branch_name: str
    base_branch: str | None = None

class GitCheckout(BaseModel):
    repo_path: str
    branch_name: str

class GitShow(BaseModel):
    repo_path: str
    revision: str

class GitClone(BaseModel):
    url: str
    path: str

class GitFetch(BaseModel):
    repo_path: str
    remote: str

class GitPull(BaseModel):
    repo_path: str
    remote: str

class GitPush(BaseModel):
    repo_path: str
    remote: str
    branch: str | None = None

class GitRemoteAdd(BaseModel):
    repo_path: str
    name: str
    url: str

class GitInit(BaseModel):
    path: str

class GitMerge(BaseModel):
    repo_path: str
    branch: str

class GitTools(str, Enum):
    STATUS = "git_status"
    DIFF_UNSTAGED = "git_diff_unstaged"
    DIFF_STAGED = "git_diff_staged"
    DIFF = "git_diff"
    COMMIT = "git_commit"
    ADD = "git_add"
    RESET = "git_reset"
    LOG = "git_log"
    CREATE_BRANCH = "git_create_branch"
    CHECKOUT = "git_checkout"
    SHOW = "git_show"
    CLONE = "git_clone"
    FETCH = "git_fetch"
    PULL = "git_pull"
    PUSH = "git_push"
    REMOTE_ADD = "git_remote_add"
    MERGE = "git_merge"
    INIT = "git_init"
    
def git_status(repo: git.Repo) -> str:
    return repo.git.status()

def git_diff_unstaged(repo: git.Repo) -> str:
    return repo.git.diff()

def git_diff_staged(repo: git.Repo) -> str:
    return repo.git.diff("--cached")

def git_diff(repo: git.Repo, target: str) -> str:
    return repo.git.diff(target)

def git_commit(repo: git.Repo, message: str) -> str:
    commit = repo.index.commit(message)
    return f"Changes committed successfully with hash {commit.hexsha}"

def git_add(repo: git.Repo, files: list[str]) -> str:
    repo.index.add(files)
    return "Files staged successfully"

def git_reset(repo: git.Repo) -> str:
    repo.index.reset()
    return "All staged changes reset"

def git_log(repo: git.Repo, max_count: int = 10) -> list[str]:
    commits = list(repo.iter_commits(max_count=max_count))
    log = []
    for commit in commits:
        log.append(
            f"Commit: {commit.hexsha}\n"
            f"Author: {commit.author}\n"
            f"Date: {commit.authored_datetime}\n"
            f"Message: {commit.message}\n"
        )
    return log

def git_create_branch(repo: git.Repo, branch_name: str, base_branch: str | None = None) -> str:
    if base_branch:
        base = repo.refs[base_branch]
    else:
        base = repo.active_branch

    repo.create_head(branch_name, base)
    return f"Created branch '{branch_name}' from '{base.name}'"

def git_checkout(repo: git.Repo, branch_name: str) -> str:
    repo.git.checkout(branch_name)
    return f"Switched to branch '{branch_name}'"

def git_init(repo_path: str) -> str:
    try:
        repo = git.Repo.init(path=repo_path, mkdir=True)
        return f"Initialized empty Git repository in {repo.git_dir}"
    except Exception as e:
        return f"Error initializing repository: {str(e)}"

def git_show(repo: git.Repo, revision: str) -> str:
    commit = repo.commit(revision)
    output = [
        f"Commit: {commit.hexsha}\n"
        f"Author: {commit.author}\n"
        f"Date: {commit.authored_datetime}\n"
        f"Message: {commit.message}\n"
    ]
    if commit.parents:
        parent = commit.parents[0]
        diff = parent.diff(commit, create_patch=True)
    else:
        diff = commit.diff(git.NULL_TREE, create_patch=True)
    for d in diff:
        output.append(f"\n--- {d.a_path}\n+++ {d.b_path}\n")
        output.append(d.diff.decode('utf-8'))
    return "".join(output)

def git_clone(url: str, path: str) -> str:
    try:
        git.Repo.clone_from(url, path)
        return f"Cloned repository from {url} to {path}"
    except git.GitCommandError as e:
        return f"Clone failed: {str(e)}"

def git_fetch(repo: git.Repo, remote: str) -> str:
    repo.git.fetch(remote)
    return f"Fetched from {remote}"

def git_pull(repo: git.Repo, remote: str) -> str:
    repo.git.pull(remote)
    return f"Pulled from {remote}"

def git_push(repo: git.Repo, remote: str, branch: str | None = None) -> str:
    try:
        if branch:
            repo.git.push(remote, branch)
        else:
            repo.git.push(remote)
        return f"Pushed to {remote}"
    except git.GitCommandError as e:
        return f"Push failed: {str(e)}"

def git_remote_add(repo: git.Repo, name: str, url: str) -> str:
    repo.create_remote(name, url)
    return f"Added remote {name} with URL {url}"

def git_merge(repo: git.Repo, branch: str) -> str:
    try:
        repo.git.merge(branch)
        return f"Successfully merged {branch}"
    except git.GitCommandError as e:
        return f"Merge failed: {str(e)}"

async def serve(repository: Path | None) -> None:
    logger = logging.getLogger(__name__)

    # if repository is not None:
    #     try:
    #         git.Repo(repository)
    #         logger.info(f"Using repository at {repository}")
    #     except git.InvalidGitRepositoryError:
    #         logger.error(f"{repository} is not a valid Git repository")
    #         return

    server = Server("mcp-git")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=GitTools.STATUS,
                description="Shows the working tree status",
                inputSchema=GitStatus.schema(),
            ),
            Tool(
                name=GitTools.DIFF_UNSTAGED,
                description="Shows changes in the working directory that are not yet staged",
                inputSchema=GitDiffUnstaged.schema(),
            ),
            Tool(
                name=GitTools.DIFF_STAGED,
                description="Shows changes that are staged for commit",
                inputSchema=GitDiffStaged.schema(),
            ),
            Tool(
                name=GitTools.DIFF,
                description="Shows differences between branches or commits",
                inputSchema=GitDiff.schema(),
            ),
            Tool(
                name=GitTools.COMMIT,
                description="Records changes to the repository",
                inputSchema=GitCommit.schema(),
            ),
            Tool(
                name=GitTools.ADD,
                description="Adds file contents to the staging area",
                inputSchema=GitAdd.schema(),
            ),
            Tool(
                name=GitTools.RESET,
                description="Unstages all staged changes",
                inputSchema=GitReset.schema(),
            ),
            Tool(
                name=GitTools.LOG,
                description="Shows the commit logs",
                inputSchema=GitLog.schema(),
            ),
            Tool(
                name=GitTools.CREATE_BRANCH,
                description="Creates a new branch from an optional base branch",
                inputSchema=GitCreateBranch.schema(),
            ),
            Tool(
                name=GitTools.CHECKOUT,
                description="Switches branches",
                inputSchema=GitCheckout.schema(),
            ),
            Tool(
                name=GitTools.SHOW,
                description="Shows the contents of a commit",
                inputSchema=GitShow.schema(),
            ),
            Tool(
                name=GitTools.INIT,
                description="Initialize a new Git repository",
                inputSchema=GitInit.schema(),
            ),
            Tool(
                name=GitTools.CLONE,
                description="Clones a repository from a URL",
                inputSchema=GitClone.schema(),
            ),
            Tool(
                name=GitTools.FETCH,
                description="Fetches from a remote repository",
                inputSchema=GitFetch.schema(),
            ),
            Tool(
                name=GitTools.PULL,
                description="Pulls from a remote repository",
                inputSchema=GitPull.schema(),
            ),
            Tool(
                name=GitTools.PUSH,
                description="Pushes to a remote repository",
                inputSchema=GitPush.schema(),
            ),
            Tool(
                name=GitTools.REMOTE_ADD,
                description="Adds a new remote repository",
                inputSchema=GitRemoteAdd.schema(),
            ),
            Tool(
                name=GitTools.MERGE,
                description="Merges specified branch into current branch",
                inputSchema=GitMerge.schema(),
            )
        ]

    async def list_repos() -> Sequence[str]:
        async def by_roots() -> Sequence[str]:
            if not isinstance(server.request_context.session, ServerSession):
                raise TypeError("server.request_context.session must be a ServerSession")

            if not server.request_context.session.check_client_capability(
                ClientCapabilities(roots=RootsCapability())
            ):
                return []

            roots_result: ListRootsResult = await server.request_context.session.list_roots()
            logger.debug(f"Roots result: {roots_result}")
            repo_paths = []
            for root in roots_result.roots:
                path = root.uri.path
                try:
                    git.Repo(path)
                    repo_paths.append(str(path))
                except git.InvalidGitRepositoryError:
                    pass
            return repo_paths

        def by_commandline() -> Sequence[str]:
            return [str(repository)] if repository is not None else []

        cmd_repos = by_commandline()
        root_repos = await by_roots()
        return [*root_repos, *cmd_repos]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        repo_path = Path(arguments["repo_path"])
        
        # Handle git init separately since it doesn't require an existing repo
        if name == GitTools.INIT:
            result = git_init(str(repo_path))
            return [TextContent(
                type="text",
                text=result
            )]
            
        # For all other commands, we need an existing repo
        repo = git.Repo(repo_path)

        match name:
            case GitTools.STATUS:
                status = git_status(repo)
                return [TextContent(
                    type="text",
                    text=f"Repository status:\n{status}"
                )]

            case GitTools.DIFF_UNSTAGED:
                diff = git_diff_unstaged(repo)
                return [TextContent(
                    type="text",
                    text=f"Unstaged changes:\n{diff}"
                )]

            case GitTools.DIFF_STAGED:
                diff = git_diff_staged(repo)
                return [TextContent(
                    type="text",
                    text=f"Staged changes:\n{diff}"
                )]

            case GitTools.DIFF:
                diff = git_diff(repo, arguments["target"])
                return [TextContent(
                    type="text",
                    text=f"Diff with {arguments['target']}:\n{diff}"
                )]

            case GitTools.COMMIT:
                result = git_commit(repo, arguments["message"])
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.ADD:
                result = git_add(repo, arguments["files"])
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.RESET:
                result = git_reset(repo)
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.LOG:
                log = git_log(repo, arguments.get("max_count", 10))
                return [TextContent(
                    type="text",
                    text="Commit history:\n" + "\n".join(log)
                )]

            case GitTools.CREATE_BRANCH:
                result = git_create_branch(
                    repo,
                    arguments["branch_name"],
                    arguments.get("base_branch")
                )
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.CHECKOUT:
                result = git_checkout(repo, arguments["branch_name"])
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.SHOW:
                result = git_show(repo, arguments["revision"])
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.CLONE:
                result = git_clone(arguments["url"], arguments["path"])
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.FETCH:
                result = git_fetch(repo, arguments["remote"])
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.PULL:
                result = git_pull(repo, arguments["remote"])
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.PUSH:
                result = git_push(repo, arguments["remote"], arguments.get("branch"))
                return [TextContent(
                    type="text",
                    text=result
                )]
            case GitTools.REMOTE_ADD:
                result = git_remote_add(repo, arguments["name"], arguments["url"])
                return [TextContent(
                    type="text",
                    text=result
                )]

            case GitTools.MERGE:
                result = git_merge(repo, arguments["branch"])
                return [TextContent(
                    type="text",
                    text=result
                )]
            case GitTools.INIT:
                result = git_init(arguments["path"])
                return [TextContent(
                    type="text",
                    text=result
                )]
            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)

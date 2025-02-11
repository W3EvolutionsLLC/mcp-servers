from enum import Enum
from pydantic import BaseModel

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

class GitMerge(BaseModel):
    repo_path: str
    branch: str

class W3GitTools():
    CLONE = "git_clone"
    FETCH = "git_fetch"
    PULL = "git_pull"
    PUSH = "git_push"
    REMOTE_ADD = "git_remote_add"
    MERGE = "git_merge"
    
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
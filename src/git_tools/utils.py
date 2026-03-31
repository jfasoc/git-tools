import subprocess
import sys


def run_git_command(args, repo_path=None, input=None):
    """
    Run a git command and return its output.

    Args:
        args (list): List of command line arguments for git.
        repo_path (str, optional): Path to the repository.
        input (str, optional): String to be passed to stdin.

    Returns:
        str: The stdout of the command.

    Raises:
        SystemExit: If the git command fails or is not found.
    """
    try:
        cmd = ["git"]
        if repo_path:
            cmd.extend(["-C", repo_path])
        cmd.extend(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, input=input
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: git command not found.", file=sys.stderr)
        sys.exit(1)

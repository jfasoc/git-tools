import sys
import os
import shtab

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from git_tools.commit_stats import get_parser as get_commit_parser
from git_tools.pack_stats import get_parser as get_pack_parser

def generate():
    # Git commit stats
    cp = get_commit_parser()
    cp.prog = "git-commit-stats"
    # Use shtab's add_argument().complete to specify directory completion
    cp._actions[1].complete = shtab.DIR

    # Git pack stats
    pp = get_pack_parser()
    pp.prog = "git-pack-stats"
    pp._actions[1].complete = shtab.DIR

    commit_bash = shtab.complete(cp, shell="bash")
    pack_bash = shtab.complete(pp, shell="bash")

    with open("completions/git-tools.bash", "w") as f:
        f.write("# Bash completion for git-tools\n\n")
        f.write(commit_bash)
        f.write("\n")
        f.write(pack_bash)

    # Zsh
    commit_zsh = shtab.complete(cp, shell="zsh")
    pack_zsh = shtab.complete(pp, shell="zsh")

    with open("completions/git-tools.zsh", "w") as f:
        f.write("# Zsh completion for git-tools\n\n")
        f.write(commit_zsh)
        f.write("\n")
        f.write(pack_zsh)

if __name__ == "__main__":
    generate()

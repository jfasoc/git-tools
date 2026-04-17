#!/bin/bash
set -e

# Install PDM
pip install --user pdm
export PATH="$HOME/.local/bin:$PATH"

# Install dependencies
pdm install

# Get the absolute path of the workspace
WORKSPACE_DIR=$(pwd)

# Configure PATH and completions for Bash
cat << EOF >> ~/.bashrc

# Git Tools configuration
export PATH="\$HOME/.local/bin:${WORKSPACE_DIR}/.venv/bin:\$PATH"
if [ -f "${WORKSPACE_DIR}/completions/git-tools.bash" ]; then
    source "${WORKSPACE_DIR}/completions/git-tools.bash"
fi
EOF

# Configure PATH and completions for Zsh
cat << EOF >> ~/.zshrc

# Git Tools configuration
export PATH="\$HOME/.local/bin:${WORKSPACE_DIR}/.venv/bin:\$PATH"
if [ -f "${WORKSPACE_DIR}/completions/git-tools.zsh" ]; then
    source "${WORKSPACE_DIR}/completions/git-tools.zsh"
fi
EOF

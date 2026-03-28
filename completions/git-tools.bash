_git_tools_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="-h --help"

    # Only provide completions if it's the first argument after the command name
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        if [[ ${cur} == -* ]]; then
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
        fi

        # Suggest directories for the repository path
        COMPREPLY=( $(compgen -d -- ${cur}) )
        return 0
    fi
}

complete -F _git_tools_completion git-commit-stats
complete -F _git_tools_completion git-pack-stats

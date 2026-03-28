_git_tools_completion() {
    local -a opts
    opts=(
        '(-h --help)'{-h,--help}'[show help message and exit]'
        '1:repository path:_directories'
    )

    _arguments -s : $opts
}

compdef _git_tools_completion git-commit-stats git-pack-stats

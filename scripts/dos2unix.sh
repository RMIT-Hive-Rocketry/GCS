find ./ -type f \
        -not -path './__pycache__*' \
        -a -not -path '*.git*' \
        -a -not -path './.pytest_cache*' \
        -a -not -path './.venv*' \
        -a -not -path './node_modules*' \
        -a -not -name '*~' \
        -exec dos2unix '{}' '+'

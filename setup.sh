#!/usr/bin/env bash

CLI_PYTHON_FILE="rocket.py"
EXEC_NAME="rocket"
PROTOBUF_VERSION="30.1"
PROTOBUF_MAJOR_VERSION="30"
PYTHON_VERSION="3.11"

# collect opts
AUTO_YES=0 # for CI

while getopts "y" opt; do
    case $opt in

    y) AUTO_YES=1 ;;

    esac
done

# helper functions

ask() {
    if [[ $AUTO_YES -eq 1 ]]; then
        return 0
    fi

    REPLY=""
    read -p "$1 (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    fi

    return 1
}

error() {
    echo $@ >&2
}

# setup functions

protobuf_installed() {
    if ! command -v protoc &>/dev/null; then
        return 1
    fi

    protoc_version=$(protoc --version | awk '{print $2}')
    protoc_major_version=$(echo $protoc_version | cut -d. -f1)

    if [[ $protoc_major_version == "$PROTOBUF_MAJOR_VERSION" ]]; then
        return 0
    else
        echo "Found protobuf version $protoc_version, but major version $PROTOBUF_MAJOR_VERSION is required." >&2
        return 1
    fi
}

install_protobuf() {
    if ! command -v git &>/dev/null; then
        error "Error: git is not installed. Please install git to proceed with protobuf installation."
        return 1
    fi

    if ! command -v cmake &>/dev/null; then
        error "Error: cmake is not installed. Please install cmake to proceed with protobuf installation."
        return 1
    fi

    if ! command -v make &>/dev/null; then
        error "Error: make is not installed. Please install make to proceed with protobuf installation."
        return 1
    fi

    ORIGINAL_DIR="$(pwd)"
    echo "Installing protobuf v$PROTOBUF_VERSION..."

    # Create temp directory for protobuf if it doesn't exist
    if [ -d "$HOME/protobuf" ]; then
        echo "Warning: $HOME/protobuf directory already exists."

        if ask "Do you want to remove it and continue with installation?"; then
            rm -rf "$HOME/protobuf"
        else
            echo "Warning: $HOME/protobuf directory already exists."
            read -p "Do you want to remove it and continue with installation? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$HOME/protobuf"
            else
                echo "Skipping protobuf installation."
                return 1
            fi
        fi
    fi

    git clone https://github.com/protocolbuffers/protobuf.git "$HOME/protobuf"
    if [ $? -ne 0 ]; then
        error "Error: Failed to clone protobuf repository."
        return 1
    fi

    cd "$HOME/protobuf"
    git checkout "v$PROTOBUF_VERSION"
    if [ $? -ne 0 ]; then
        error "Error: Failed to checkout protobuf v$PROTOBUF_VERSION."
        cd - >/dev/null
        return 1
    fi

    git submodule update --init --recursive
    if [ $? -ne 0 ]; then
        error "Error: Failed to update protobuf submodules."
        cd - >/dev/null
        return 1
    fi

    mkdir -p build && cd build
    # make sure protobuf compiles with C++17
    cmake -Dprotobuf_BUILD_TESTS=OFF \
        -DCMAKE_CXX_STANDARD=17 \
        -DCMAKE_CXX_STANDARD_REQUIRED=ON \
        -DCMAKE_CXX_EXTENSIONS=OFF \
        ..

    if [ $? -ne 0 ]; then
        error "Error: CMAKE configuration failed."
        cd - >/dev/null
        return 1
    fi

    sudo make install -j$(nproc)
    if [ $? -ne 0 ]; then
        error "Error: Failed to install protobuf. Make sure you have sudo privileges."
        cd - >/dev/null
        return 1
    fi

    if command -v ldconfig &>/dev/null; then
        sudo ldconfig
    elif command -v update_dyld_shared_cache &>/dev/null; then
        sudo update_dyld_shared_cache
    fi
    echo "Protobuf v$PROTOBUF_VERSION installation completed successfully."

    # Return to original directory
    cd "$ORIGINAL_DIR"
    return 0
}

python_installed() {
    candidates=(
        python3.11
        python3
        python
    )

    for cmd in "${candidates[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            continue
        fi

        # this is the most consistent way to check version
        version=$("$cmd" -c "import sys; print(sys.version_info[:2])" 2>/dev/null)

        if [[ "$version" == "(3, 11)" ]]; then
            echo "$cmd"
            return 0
        fi
    done

    return 1
}

install_symlink() {
    if [ ! -d "/usr/local/bin" ]; then
        error "/usr/local/bin not found. You may need to add rocket manually to your $PATH."
        return 1
    fi

    # NOTE: Using relative paths for now. No need to add this to PATH
    sudo ln -sf "$(pwd)/$CLI_PYTHON_FILE" /usr/local/bin/$EXEC_NAME
    if [ $? -ne 0 ]; then
        error "Error: Failed to create symlink. Please ensure you have the correct privileges"
        return 1
    fi

    return 0
}

setup_venv() {
    $1 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pip install -r backend/tests/requirements.txt
}

# main logic

# check python 3.11 is installed
PYTHON_CMD=$(python_installed) # save for venv setup
if [ -z "$PYTHON_CMD" ]; then
    error "Python $PYTHON_VERSION not found. Please ensure python$PYTHON_VERSION is installed and added to PATH."
    exit 1
else
    echo "Found Python $PYTHON_VERSION. ($PYTHON_CMD)"
fi

# setup python venv
if ask "Do you want to setup a python virtual environment?"; then
    setup_venv "$PYTHON_CMD"
fi

# check protobuf is installed
if ! protobuf_installed; then
    error "Protobuf $PROTOBUF_VERSION not found."

    if ask "Do you want to install protobuf v$PROTOBUF_VERSION?"; then
        install_protobuf
    fi
else
    echo "Found Protobuf $PROTOBUF_VERSION."
fi

# create rocket symlink
if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
    if ask "Do you want to add the rocket symbolic link?"; then
        install_symlink
    fi
fi

echo "Setup completed"

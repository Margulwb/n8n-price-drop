#!/bin/bash
set -e

# CONFIGURATION
WORK_DIR="/opt/custom_folder/precommit_env"
HOOKS_DIR="$WORK_DIR/git-hooks"
VENV_DIR="$WORK_DIR/venv"

# ARGUMENT HANDLING
if [ -n "$1" ]; then
    echo "Target repository path provided: $1"
    if [ -d "$1" ]; then
        cd "$1"
        echo "Changed directory to: $(pwd)"
    else
        echo "Error: Directory $1 does not exist."
        exit 1
    fi
else
    echo "No path provided. Using current directory."
fi

# VALIDATION
if [ ! -d ".git" ]; then
    echo "Error: .git directory not found in $(pwd). Is this a git repository?"
    exit 1
fi

echo "Starting pre-commit setup..."

mkdir -p "$HOOKS_DIR"
mkdir -p "$VENV_DIR"

if [ ! -f "$VENV_DIR/bin/pre-commit" ]; then
    echo "Creating virtual environment and installing pre-commit..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install pre-commit
else
    echo "Pre-commit is already installed in venv."
fi

if [ ! -f ".pre-commit-config.yaml" ]; then
    echo "Generating .pre-commit-config.yaml..."
    cat <<EOF > .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-ansible-vault
        name: Check for Ansible Vault encryption
        entry: bash -c 'grep -q "^\$ANSIBLE_VAULT;" "\$1" || (echo -e "\n[!] ERROR: File \$1 is UNENCRYPTED! Please run: ansible-vault encrypt \$1\n" && exit 1)' --
        language: system
        files: ^group_vars/secret\.yaml$
        pass_filenames: true
EOF
fi

echo "Installing git hook..."
git config --unset core.hooksPath || true
"$VENV_DIR/bin/pre-commit" install

echo "Moving hook to executable partition..."
if [ -f ".git/hooks/pre-commit" ]; then
    mv .git/hooks/pre-commit "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
else
    echo "Warning: Hook file not found in .git/hooks/ after install. It might be already in target dir."
fi

git config core.hooksPath "$HOOKS_DIR"

# PERMANENT PATH CONFIGURATION
echo "Configuring permanent PATH..."
PATH_LINE="export PATH=\"$VENV_DIR/bin:\$PATH\""
BASHRC="$HOME/.bashrc"

if ! grep -qF "$VENV_DIR/bin" "$BASHRC"; then
    echo "" >> "$BASHRC"
    echo "# Added by pre-commit setup script" >> "$BASHRC"
    echo "$PATH_LINE" >> "$BASHRC"
    echo "Added pre-commit to PATH in $BASHRC"
else
    echo "Path already configured in $BASHRC"
fi

if [ "$(git config core.hooksPath)" == "$HOOKS_DIR" ]; then
    echo "Success! Hooks are now configured in: $HOOKS_DIR"
    echo "You may need to run 'source ~/.bashrc' or restart your terminal to use the 'pre-commit' command globally."
else
    echo "Error: Failed to set core.hooksPath."
    exit 1
fi

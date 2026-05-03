#!/usr/bin/env sh
# Surfaced installer
# Usage: curl -sSL https://raw.githubusercontent.com/agentech-dev/surfaced/main/scripts/install.sh | sh
#
# Installs `surfaced` as a globally available command.
# Also installs agent CLI tools. Run `surfaced bootstrap` afterwards to set up infrastructure.

set -eu

REPO_URL="https://github.com/agentech-dev/surfaced.git"
INSTALL_DIR="$HOME/.surfaced"
LOCAL_BIN="$HOME/.local/bin"
BUN_BIN="$HOME/.bun/bin"

info()  { printf "==> %s\n" "$*"; }
ok()    { printf "  ✓ %s\n" "$*"; }
skip()  { printf "  • %s\n" "$*"; }
err()   { printf "  ✗ %s\n" "$*" >&2; }

export PATH="$LOCAL_BIN:$BUN_BIN:$PATH"

sudo_cmd() {
    if [ "$(id -u)" = "0" ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        return 1
    fi
}

install_unzip() {
    if command -v unzip >/dev/null 2>&1; then
        ok "unzip found"
        return 0
    fi

    info "Installing unzip (required by Bun on Linux)..."
    if command -v apt-get >/dev/null 2>&1; then
        if ! (sudo_cmd apt-get update -qq && sudo_cmd apt-get install -y -qq unzip); then
            err "Failed to install unzip — install manually: sudo apt-get install unzip"
            exit 1
        fi
    elif command -v dnf >/dev/null 2>&1; then
        if ! sudo_cmd dnf install -y unzip; then
            err "Failed to install unzip — install manually: sudo dnf install unzip"
            exit 1
        fi
    elif command -v yum >/dev/null 2>&1; then
        if ! sudo_cmd yum install -y unzip; then
            err "Failed to install unzip — install manually: sudo yum install unzip"
            exit 1
        fi
    elif command -v apk >/dev/null 2>&1; then
        if ! sudo_cmd apk add unzip; then
            err "Failed to install unzip — install manually: sudo apk add unzip"
            exit 1
        fi
    elif command -v brew >/dev/null 2>&1; then
        if ! brew install unzip; then
            err "Failed to install unzip — install manually: brew install unzip"
            exit 1
        fi
    else
        err "unzip is required to install Bun, but no supported package manager was found"
        echo ""
        echo "Install unzip with your system package manager, then re-run this installer."
        exit 1
    fi

    if command -v unzip >/dev/null 2>&1; then
        ok "unzip installed"
    else
        err "unzip install completed, but unzip is still not on PATH"
        exit 1
    fi
}

install_bun() {
    if command -v bun >/dev/null 2>&1; then
        ok "bun found ($(bun --version 2>/dev/null || echo installed))"
        return 0
    fi

    install_unzip
    info "Installing Bun..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$BUN_BIN:$PATH"

    if command -v bun >/dev/null 2>&1; then
        ok "bun installed ($(bun --version 2>/dev/null || echo installed))"
    else
        err "Bun installed, but $BUN_BIN is not on your PATH"
        echo ""
        echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export BUN_INSTALL=\"$HOME/.bun\""
        echo "  export PATH=\"\$BUN_INSTALL/bin:\$PATH\""
        exit 1
    fi
}

install_claude() {
    if command -v claude >/dev/null 2>&1; then
        ok "claude found"
        return 0
    fi

    info "Installing Claude Code..."
    curl -fsSL https://claude.ai/install.sh | bash
    export PATH="$LOCAL_BIN:$PATH"

    if command -v claude >/dev/null 2>&1; then
        ok "claude installed"
    else
        err "Claude Code installed, but $LOCAL_BIN is not on your PATH"
        echo ""
        echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export PATH=\"$LOCAL_BIN:\$PATH\""
        exit 1
    fi
}

install_bun_cli() {
    binary="$1"
    package="$2"

    if command -v "$binary" >/dev/null 2>&1; then
        ok "$binary found"
        return 0
    fi

    info "Installing $binary..."
    bun add --global "$package"
    export PATH="$BUN_BIN:$PATH"

    if command -v "$binary" >/dev/null 2>&1; then
        ok "$binary installed"
    else
        err "$package installed, but $binary is not on your PATH"
        echo ""
        echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export BUN_INSTALL=\"$HOME/.bun\""
        echo "  export PATH=\"\$BUN_INSTALL/bin:\$PATH\""
        exit 1
    fi
}

# ---------- 1. Check dependencies ----------
info "Checking dependencies..."

if command -v git >/dev/null 2>&1; then
    ok "git found ($(git --version 2>/dev/null | head -n1))"
else
    err "git is required but not installed"
    echo ""
    echo "Please install git, then re-run this installer:"
    echo "  macOS:   xcode-select --install   (or: brew install git)"
    echo "  Debian:  sudo apt-get install git"
    echo "  Fedora:  sudo dnf install git"
    echo ""
    exit 1
fi

if command -v uv >/dev/null 2>&1; then
    ok "uv found ($(uv --version 2>/dev/null | head -n1))"
    NEED_UV=0
else
    skip "uv not found — will install"
    NEED_UV=1
fi

# ---------- 2. Install uv if needed ----------
if [ "$NEED_UV" = "1" ]; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    ok "uv installed"
fi

# ---------- 3. Clone repo to ~/.surfaced ----------
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Updating existing installation..."
    git -C "$INSTALL_DIR" pull --quiet
    ok "Updated ~/.surfaced"
else
    if [ -d "$INSTALL_DIR" ]; then
        info "Removing stale ~/.surfaced directory..."
        rm -rf "$INSTALL_DIR"
    fi
    info "Cloning surfaced to ~/.surfaced..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    ok "Cloned to ~/.surfaced"
fi

# ---------- 4. Install as global tool ----------
info "Installing surfaced CLI..."
uv tool install --from "$INSTALL_DIR" surfaced --force --quiet
ok "surfaced installed"

# ---------- 5. Install agent CLI tools ----------
info "Installing agent CLI tools..."
install_claude
install_bun
install_bun_cli codex @openai/codex
install_bun_cli gemini @google/gemini-cli

# ---------- Verify ----------
if command -v surfaced >/dev/null 2>&1; then
    ok "surfaced $(surfaced --version 2>/dev/null || echo '') is ready"
else
    # uv tool bin might not be on PATH yet
    UV_BIN="$HOME/.local/bin"
    if [ -f "$UV_BIN/surfaced" ]; then
        err "surfaced installed but $UV_BIN is not on your PATH"
        echo ""
        echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export PATH=\"$UV_BIN:\$PATH\""
        echo ""
        echo "Then restart your shell and run: surfaced bootstrap"
        exit 0
    fi
    err "Installation failed — surfaced not found on PATH"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════"
echo " Surfaced installed!"
echo "════════════════════════════════════════════════════"
echo ""
echo " You may need to restart your shell or run:"
echo "   source ~/.bashrc    # (or ~/.zshrc)"
echo ""
echo " Then: surfaced bootstrap"
echo ""

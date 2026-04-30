#!/usr/bin/env sh
# Surfaced installer
# Usage: curl -sSL https://raw.githubusercontent.com/agentech-dev/surfaced/main/scripts/install.sh | sh
#
# Installs `surfaced` as a globally available command.
# Run `surfaced bootstrap` afterwards to set up infrastructure.

set -eu

REPO_URL="https://github.com/agentech-dev/surfaced.git"
INSTALL_DIR="$HOME/.surfaced"

info()  { printf "==> %s\n" "$*"; }
ok()    { printf "  ✓ %s\n" "$*"; }
skip()  { printf "  • %s\n" "$*"; }
err()   { printf "  ✗ %s\n" "$*" >&2; }

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

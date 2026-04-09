#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# longClaw / OpenClaw bootstrap for Mac mini M4
# - Re-runnable
# - Persists Node 20 pin into shell profile
# - Skips components that are already installed
# - Optionally initializes Playwright Test inside a repo
# ============================================================

REPO_PATH="${1:-}"
BREW_PREFIX="/opt/homebrew"
NODE_FORMULA="node@20"
NODE_MAJOR_TARGET="20"
NODE_FALLBACK_ROOT="$HOME/.longclaw/node20"
NODE_FALLBACK_CURRENT="$NODE_FALLBACK_ROOT/current"
ZPROFILE="$HOME/.zprofile"
BASH_PROFILE="$HOME/.bash_profile"
PLAYWRIGHT_SKILLS_MARKER="$HOME/.longclaw-bootstrap/playwright-skills.done"

log()  { printf "\n[INFO] %s\n" "$*"; }
ok()   { printf "[ OK ] %s\n" "$*"; }
warn() { printf "[WARN] %s\n" "$*"; }
die()  { printf "[FAIL] %s\n" "$*" >&2; exit 1; }

trap 'die "脚本在第 $LINENO 行失败。请检查上面的输出。"' ERR

ensure_file() {
  local file="$1"
  mkdir -p "$(dirname "$file")"
  touch "$file"
}

append_line_if_missing() {
  local file="$1"
  local line="$2"
  ensure_file "$file"
  if grep -Fq "$line" "$file"; then
    ok "$file 已包含: $line"
  else
    printf '\n%s\n' "$line" >> "$file"
    ok "已写入 $file: $line"
  fi
}

append_block_if_missing() {
  local file="$1"
  local marker="$2"
  local block="$3"
  ensure_file "$file"
  if grep -Fq "$marker" "$file"; then
    ok "$file 已包含 $marker"
  else
    printf '\n%s\n' "$block" >> "$file"
    ok "已写入 $file: $marker"
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

current_node_major() {
  if command_exists node; then
    node -p "process.versions.node.split('.')[0]" 2>/dev/null || true
  fi
}

load_shell_profiles_best_effort() {
  local file
  for file in "$ZPROFILE" "$HOME/.zshrc" "$BASH_PROFILE" "$HOME/.profile"; do
    if [[ -f "$file" ]]; then
      # shellcheck disable=SC1090
      . "$file" || true
    fi
  done
}

install_xcode_clt_if_needed() {
  if xcode-select -p >/dev/null 2>&1; then
    ok "Xcode Command Line Tools 已安装"
    return
  fi

  log "安装 Xcode Command Line Tools（会弹系统对话框）..."
  xcode-select --install || true
  warn "如果弹出安装窗口，请点 Install。安装完成后重新运行本脚本。"

  for _ in $(seq 1 240); do
    if xcode-select -p >/dev/null 2>&1; then
      ok "Xcode Command Line Tools 安装完成"
      return
    fi
    sleep 5
  done

  die "等待 Xcode Command Line Tools 安装超时。请安装完成后重新运行脚本。"
}

install_homebrew_if_needed() {
  if [[ -x "$BREW_PREFIX/bin/brew" ]]; then
    ok "Homebrew 已安装"
  else
    log "安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ok "Homebrew 安装完成"
  fi

  append_line_if_missing "$ZPROFILE" 'eval "$(/opt/homebrew/bin/brew shellenv)"'
  append_line_if_missing "$BASH_PROFILE" 'eval "$(/opt/homebrew/bin/brew shellenv)"'

  # shellcheck disable=SC1091
  eval "$("$BREW_PREFIX/bin/brew" shellenv)"
  command_exists brew || die "brew 未加入当前 shell PATH"
  ok "Homebrew 已加入当前 shell PATH"
}

pin_node20_in_profiles() {
  local block
  block=$(cat <<'EOF'
# >>> longclaw node20 >>>
if [ -d "$HOME/.longclaw/node20/current/bin" ]; then
  export PATH="$HOME/.longclaw/node20/current/bin:$PATH"
fi
export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
# <<< longclaw node20 <<<
EOF
)
  append_block_if_missing "$ZPROFILE" '# >>> longclaw node20 >>>' "$block"
  append_block_if_missing "$BASH_PROFILE" '# >>> longclaw node20 >>>' "$block"
}

brew_node20_present() {
  [[ -x "$BREW_PREFIX/opt/$NODE_FORMULA/bin/node" ]]
}

detect_latest_node20_version() {
  python3 <<'PYEOF'
import json
import urllib.request

with urllib.request.urlopen("https://nodejs.org/dist/index.json", timeout=30) as resp:
    releases = json.load(resp)

for item in releases:
    version = item.get("version", "")
    files = set(item.get("files", []))
    if version.startswith("v20.") and "osx-arm64-tar" in files:
        print(version)
        break
PYEOF
}

install_node20_official() {
  local version archive url tmpdir release_dir

  version="$(detect_latest_node20_version)"
  [[ -n "$version" ]] || die "无法获取最新 Node 20 版本"

  archive="node-${version}-darwin-arm64.tar.gz"
  url="https://nodejs.org/dist/${version}/${archive}"
  tmpdir="$(mktemp -d)"
  release_dir="$NODE_FALLBACK_ROOT/releases/${version}"

  mkdir -p "$NODE_FALLBACK_ROOT/releases"

  log "通过 Node 官方发布包安装 ${version}（绕过 Homebrew portable-ruby 下载）"
  curl -fsSL "$url" -o "$tmpdir/$archive"
  tar -xzf "$tmpdir/$archive" -C "$tmpdir"

  rm -rf "$release_dir"
  mv "$tmpdir/node-${version}-darwin-arm64" "$release_dir"
  ln -sfn "$release_dir" "$NODE_FALLBACK_CURRENT"
  rm -rf "$tmpdir"

  ok "官方 Node 20 安装完成: ${version}"
}

ensure_node20_runtime() {
  pin_node20_in_profiles

  export PATH="$NODE_FALLBACK_CURRENT/bin:$BREW_PREFIX/opt/$NODE_FORMULA/bin:$PATH"
  hash -r

  local major
  major="$(current_node_major)"
  if [[ "$major" == "$NODE_MAJOR_TARGET" ]]; then
    ok "Node 已固定到: $(node -v)"
    ok "npm 版本: $(npm -v)"
    return
  fi

  if brew_node20_present; then
    ok "检测到 Homebrew 的 $NODE_FORMULA"
  else
    install_node20_official
  fi

  export PATH="$NODE_FALLBACK_CURRENT/bin:$BREW_PREFIX/opt/$NODE_FORMULA/bin:$PATH"
  hash -r

  major="$(current_node_major)"
  if [[ "$major" != "$NODE_MAJOR_TARGET" ]]; then
    die "Node 版本不是期望的 $NODE_MAJOR_TARGET.x，当前是: $(node -v 2>/dev/null || echo 'unknown')"
  fi

  ok "Node 已固定到: $(node -v)"
  ok "npm 版本: $(npm -v)"
}

ensure_brew_formula() {
  local formula="$1"
  if command_exists "$formula"; then
    ok "$formula 已安装: $(command -v "$formula")"
    return
  fi

  log "安装 Homebrew 包: $formula"
  brew install "$formula"
  ok "$formula 安装完成"
}

ensure_npm_command() {
  local cmd="$1"
  local package="$2"

  if command_exists "$cmd"; then
    ok "$cmd 已安装: $(command -v "$cmd")"
    return
  fi

  log "安装全局 npm 包: $package"
  npm install -g "$package"

  if command_exists "$cmd"; then
    ok "$cmd 安装完成: $(command -v "$cmd")"
  else
    die "$package 安装后仍找不到命令: $cmd"
  fi
}

ensure_uv() {
  if command_exists uv; then
    ok "uv 已安装: $(uv --version)"
    return
  fi

  log "安装 uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  load_shell_profiles_best_effort

  if command_exists uv; then
    ok "uv 已安装: $(uv --version)"
  else
    warn "uv 已安装，但当前 shell 可能还没拿到 PATH。稍后执行: source ~/.zprofile"
  fi
}

ensure_playwright_skills() {
  mkdir -p "$(dirname "$PLAYWRIGHT_SKILLS_MARKER")"

  if [[ -f "$PLAYWRIGHT_SKILLS_MARKER" ]] && command_exists playwright-cli; then
    ok "Playwright skills 已安装（marker: $PLAYWRIGHT_SKILLS_MARKER）"
    return
  fi

  log "安装 Playwright skills"
  playwright-cli install --skills
  date '+%Y-%m-%d %H:%M:%S %z' > "$PLAYWRIGHT_SKILLS_MARKER"
  ok "Playwright skills 安装完成"
}

repo_has_playwright_test() {
  npm ls @playwright/test --depth=0 >/dev/null 2>&1
}

maybe_init_playwright_test() {
  if [[ -z "$REPO_PATH" ]]; then
    warn "未提供仓库路径，跳过 Playwright Test 初始化"
    return
  fi

  [[ -d "$REPO_PATH" ]] || die "仓库路径不存在: $REPO_PATH"
  cd "$REPO_PATH"

  if [[ ! -f package.json ]]; then
    log "仓库中没有 package.json，先初始化 npm"
    npm init -y >/dev/null 2>&1
    ok "已生成 package.json"
  else
    ok "仓库已有 package.json"
  fi

  if repo_has_playwright_test; then
    ok "仓库已安装 @playwright/test"
  else
    log "安装仓库内 Playwright Test"
    npm install -D @playwright/test@latest
    ok "已安装 @playwright/test"
  fi

  log "安装 Playwright 浏览器"
  npx playwright install
  ok "仓库内 Playwright 浏览器安装完成"
}

print_versions() {
  printf '\n========== 当前版本 ==========\n'
  printf 'node:            %s\n' "$(node -v 2>/dev/null || echo 'missing')"
  printf 'npm:             %s\n' "$(npm -v 2>/dev/null || echo 'missing')"
  printf 'jq:              %s\n' "$(jq --version 2>/dev/null || echo 'missing')"
  printf 'uv:              %s\n' "$(uv --version 2>/dev/null || echo 'missing')"
  printf 'claude:          %s\n' "$(claude --version 2>/dev/null || echo 'missing')"
  printf 'codex:           %s\n' "$(codex --version 2>/dev/null || echo 'missing')"
  printf 'playwright-cli:  %s\n' "$(playwright-cli --version 2>/dev/null || echo 'missing')"
  printf '================================\n'
}

print_next_steps() {
  cat <<'EOF'

============================================================
Bootstrap 完成。

建议你接着做这几步：

1) 让当前终端拿到持久化配置
   source ~/.zprofile

2) 验证 Node 已固定到 20.x
   node -v
   which node

3) 登录 Claude Code
   claude

4) 登录 Codex CLI
   codex --login

5) 验证 Playwright CLI
   playwright-cli --version
   playwright-cli open https://demo.playwright.dev/todomvc/ --headed

6) 如果你传了 longClaw 仓库路径，再试：
   cd /path/to/longClaw
   npx playwright --version

7) 如果你要恢复 Brave 检索，而不是退化到网页 fallback：
   export BRAVE_API_KEY=你的key
   # 再写入你的 shell profile 做持久化

可选安装（本地模型兜底）：
- Ollama 建议继续单独用官方 macOS 安装方式处理，不放进这个脚本里。

EOF
}

main() {
  log "开始初始化 longClaw / OpenClaw 本地开发环境（Mac mini M4）"
  install_xcode_clt_if_needed
  install_homebrew_if_needed
  ensure_node20_runtime
  ensure_brew_formula jq
  ensure_npm_command claude @anthropic-ai/claude-code
  ensure_npm_command codex @openai/codex
  ensure_npm_command playwright-cli @playwright/cli@latest
  ensure_uv
  ensure_playwright_skills
  maybe_init_playwright_test
  print_versions
  print_next_steps
}

main "$@"

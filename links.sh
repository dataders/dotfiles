#!/usr/bin/env zsh

set -u

mode="${1:-apply}"
script_path="${0:A}"
repo_root="${DOTFILES_ROOT:-${script_path:h}}"
home_root="${DOTFILES_HOME:-$HOME}"
env_root="${DOTFILES_ENV:-$home_root/Developer/dotfiles_env}"
developer_root="${DOTFILES_DEVELOPER:-$home_root/Developer}"
manifest="${DOTFILES_MANIFEST:-$repo_root/links.tsv}"
failures=0

usage() {
    cat <<EOF
Usage: links.sh [apply|dry-run|check|unlink|doctor]

Modes:
  apply    Create or update managed symlinks. Default.
  dry-run  Print planned symlink changes without touching the filesystem.
  check    Verify managed symlinks point to expected targets.
  unlink   Remove only managed symlinks that point to expected targets.
  doctor   Run link checks plus shell/tool/private-config health checks.
EOF
}

log() {
    print -r -- "$*"
}

fail() {
    failures=$((failures + 1))
    print -r -- "FAIL $*" >&2
}

expand_path() {
    local spec="$1"

    case "$spec" in
        repo:*) print -r -- "$repo_root/${spec#repo:}" ;;
        env:*) print -r -- "$env_root/${spec#env:}" ;;
        home:*) print -r -- "$home_root/${spec#home:}" ;;
        developer:*) print -r -- "$developer_root/${spec#developer:}" ;;
        app:*) print -r -- "$home_root/Library/Application Support/${spec#app:}" ;;
        abs:*) print -r -- "${spec#abs:}" ;;
        *)
            fail "unknown path prefix: $spec"
            print -r -- "$spec"
            ;;
    esac
}

ensure_parent() {
    local target="$1"
    local parent="${target:h}"

    if [[ "$mode" == "dry-run" ]]; then
        log "DRY-RUN mkdir -p $parent"
    elif [[ "$mode" == "apply" ]]; then
        mkdir -p "$parent"
    fi
}

safe_remove_existing_skill_dir() {
    local target="$1"

    [[ "$mode" == "apply" ]] || return 0
    [[ -e "$target" && ! -L "$target" ]] || return 0

    case "$target" in
        "$home_root/.codex/skills/"*|"$home_root/.claude/skills/"*)
            rm -rf "$target"
            ;;
        *)
            fail "refusing to replace non-symlink target: $target"
            return 1
            ;;
    esac
}

link_item() {
    local source="$1"
    local target="$2"
    local group="${3:-misc}"
    local visibility="${4:-public}"
    local note="${5:-}"
    local current=""

    case "$mode" in
        dry-run)
            ensure_parent "$target"
            log "DRY-RUN ln -sfn $source $target [$group/$visibility] $note"
            ;;
        apply)
            ensure_parent "$target"
            safe_remove_existing_skill_dir "$target" || return 0
            ln -sfn "$source" "$target"
            log "LINK $target -> $source"
            ;;
        check)
            if [[ ! -L "$target" ]]; then
                fail "$target is not a symlink to $source"
                return 0
            fi

            current="$(readlink "$target")"
            if [[ "$current" != "$source" ]]; then
                fail "$target points to $current, expected $source"
            else
                log "OK $target -> $source"
            fi
            ;;
        unlink)
            if [[ ! -e "$target" && ! -L "$target" ]]; then
                log "MISSING $target"
                return 0
            fi

            if [[ ! -L "$target" ]]; then
                fail "refusing to remove non-symlink target: $target"
                return 0
            fi

            current="$(readlink "$target")"
            if [[ "$current" != "$source" ]]; then
                fail "refusing to remove $target; points to $current, expected $source"
                return 0
            fi

            rm "$target"
            log "UNLINK $target"
            ;;
        *)
            fail "unknown mode: $mode"
            ;;
    esac
}

process_manifest() {
    local source_spec target_spec group visibility note source target

    if [[ ! -f "$manifest" ]]; then
        fail "manifest not found: $manifest"
        return 0
    fi

    while IFS=$'\t' read -r source_spec target_spec group visibility note || [[ -n "$source_spec" ]]; do
        [[ -z "$source_spec" || "$source_spec" == \#* ]] && continue

        source="$(expand_path "$source_spec")"
        target="$(expand_path "$target_spec")"
        link_item "$source" "$target" "$group" "$visibility" "$note"
    done < "$manifest"
}

process_shared_skills() {
    local shared_skills_root="$repo_root/.ai/skills"
    local skill_dir skill_name

    [[ -d "$shared_skills_root" ]] || return 0

    if [[ "$mode" == "apply" || "$mode" == "dry-run" ]]; then
        if [[ "$mode" == "dry-run" ]]; then
            log "DRY-RUN mkdir -p $home_root/.codex/skills"
            log "DRY-RUN mkdir -p $home_root/.claude/skills"
        else
            mkdir -p "$home_root/.codex/skills"
            mkdir -p "$home_root/.claude/skills"
        fi
    fi

    for skill_dir in "$shared_skills_root"/*; do
        [[ -d "$skill_dir" ]] || continue
        skill_name="${skill_dir:t}"
        link_item "$skill_dir" "$home_root/.codex/skills/$skill_name" agents public "shared Codex skill"
        link_item "$skill_dir" "$home_root/.claude/skills/$skill_name" agents public "shared Claude skill"
    done
}

doctor_check() {
    local description="$1"
    shift

    if "$@" >/dev/null 2>&1; then
        log "OK $description"
    else
        fail "$description"
    fi
}

doctor_optional_file() {
    local path="$1"
    local description="$2"

    if [[ -f "$path" ]]; then
        log "OK optional $description: $path"
    else
        log "SKIP optional $description: $path"
    fi
}

doctor_private_file() {
    local path="$1"

    if [[ -e "$path" ]]; then
        log "OK private source exists: $path"
    else
        fail "missing private source: $path"
    fi
}

run_doctor() {
    local saved_mode="$mode"
    local dbt_file

    mode="check"
    process_manifest
    process_shared_skills
    mode="$saved_mode"

    doctor_check "zsh is available" command -v zsh
    doctor_check "uv is available" command -v uv
    doctor_check "direnv is available" command -v direnv
    doctor_check "starship is available" command -v starship
    doctor_check "git is available" command -v git
    doctor_check "login shell sees uv, direnv, and starship" zsh -lc 'command -v uv >/dev/null && command -v direnv >/dev/null && command -v starship >/dev/null'

    if zsh -lc 'command -v conda >/dev/null 2>&1 || command -v micromamba >/dev/null 2>&1' >/dev/null 2>&1; then
        fail "conda/micromamba found in login shell"
    else
        log "OK conda/micromamba absent from login shell"
    fi

    for dbt_file in profiles.yml dbt_cloud.yml mcp.yml keyfile.json .user.yml; do
        doctor_private_file "$env_root/.dbt/$dbt_file"
    done

    doctor_optional_file "$env_root/secrets.zsh" "zsh secrets overlay"
    doctor_optional_file "$env_root/local.zsh" "zsh local overlay"
    doctor_optional_file "$env_root/gitconfig.local" "Git local overlay"
}

case "$mode" in
    apply|dry-run|check|unlink)
        process_manifest
        process_shared_skills
        ;;
    doctor)
        run_doctor
        ;;
    -h|--help|help)
        usage
        exit 0
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac

if (( failures > 0 )); then
    exit 1
fi

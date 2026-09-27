#!/bin/sh
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Production deploys are pinned to the digest the image build pushed
# (private problems/done/2026-09-26-deploy-sha-tags-are-mutable). This
# checks the three halves of that contract in .gitlab-ci.yml: only push and
# web pipelines move :latest, the build records its digest, and the trigger
# forwards it and skips rebuilds.

set -eu

ci_config="${1:-.gitlab-ci.yml}"
failures=0

fail() {
    echo "FAIL: $1" >&2
    failures=$((failures + 1))
}

job_block() {
    awk -v job="$1" '
        $0 == job ":" { in_job = 1 }
        in_job && $0 != job ":" && /^[^[:space:]#]/ { exit }
        in_job { print }
    ' "$ci_config"
}

# Run the build job's own tag-selection snippet, so the check follows the
# behaviour rather than the spelling of the condition.
push_args_for() {
    job=$1
    source=$2
    snippet=$(job_block "$job" |
        sed -n '/PUSH_ARGS="--destination/,/^      esac$/p' |
        sed 's/^      //')
    [ -n "$snippet" ] || return 1
    CI_PIPELINE_SOURCE=$source CI_REGISTRY_IMAGE=registry.example/vauchi/app \
        IMAGE=registry.example/vauchi/app CI_COMMIT_SHA=abc123 \
        sh -c "$snippet
printf '%s' \"\$PUSH_ARGS\""
}

require_latest_only_on_push() {
    job=$1
    if ! push_args_for "$job" push >/dev/null; then
        fail "$job tag selection not found"
        return
    fi
    for source in schedule pipeline trigger api; do
        case "$(push_args_for "$job" "$source")" in
            *:latest*) fail "$job: $source rebuilds must not advance :latest" ;;
            *) echo "PASS: $job: $source rebuilds cannot advance :latest" ;;
        esac
    done
    for source in push web; do
        case "$(push_args_for "$job" "$source")" in
            *:latest*) echo "PASS: $job: $source advances :latest" ;;
            *) fail "$job: $source must advance :latest" ;;
        esac
    done
}

require_digest_forwarded() {
    build=$1
    trigger=$2
    variable=$3
    build_block=$(job_block "$build")
    trigger_block=$(job_block "$trigger")
    if printf '%s\n' "$build_block" | grep -q -- '--digest-file' &&
        printf '%s\n' "$build_block" | grep -q "printf '$variable=%s" &&
        printf '%s\n' "$build_block" | grep -q 'dotenv:'; then
        echo "PASS: $build records its pushed digest as $variable"
    else
        fail "$build must record its pushed digest as $variable (dotenv)"
    fi
    if printf '%s\n' "$trigger_block" | grep -q "DEPLOY_IMAGE_DIGEST: \\\$$variable\$"; then
        echo "PASS: $trigger forwards $variable"
    else
        fail "$trigger must forward DEPLOY_IMAGE_DIGEST: \$$variable"
    fi
}

require_rebuilds_skip_deploy() {
    trigger=$1
    block=$(job_block "$trigger")
    rebuild=$(printf '%s\n' "$block" |
        grep -n 'CI_PIPELINE_SOURCE == "pipeline"' | head -1 | cut -d: -f1 || true)
    # shellcheck disable=SC2016 # matches the literal YAML text
    default=$(printf '%s\n' "$block" |
        grep -n 'CI_COMMIT_BRANCH == \$CI_DEFAULT_BRANCH' | head -1 | cut -d: -f1 || true)
    if [ -n "$rebuild" ] && [ -n "$default" ] && [ "$rebuild" -lt "$default" ] &&
        printf '%s\n' "$block" | sed -n "${rebuild},$((rebuild + 1))p" | grep -q 'when: never'; then
        echo "PASS: $trigger excludes rebuilds before the default branch"
    else
        fail "$trigger must exclude pipeline/trigger/api rebuilds before the default branch"
    fi
}

require_latest_only_on_push build:docker
require_latest_only_on_push build:cdn-docker
require_digest_forwarded build:docker deploy:trigger LANDING_IMAGE_DIGEST
require_digest_forwarded build:cdn-docker deploy:cdn CDN_IMAGE_DIGEST
require_rebuilds_skip_deploy deploy:trigger
require_rebuilds_skip_deploy deploy:cdn

[ "$failures" -eq 0 ]

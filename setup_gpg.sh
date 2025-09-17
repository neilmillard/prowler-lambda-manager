#!/usr/bin/env bash

# =========================== #
# Unofficial Bash strict mode #
# =========================== #
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
# These produce some gotchas that you may not be used to, be sure to check out
# the above link. Especially if you use grep!
set -e # Exit on failed command
set -u # Exit on empty variable
set -o pipefail # Exit on errors, even in pipes.
IFS=$'\n\t'

import_gpg_key() {
  set -e
  if [[ -z "${GPG_KEY_ID:-}" ]]; then
    GPG_SECRET_KEY_FILE="$(mktemp)"
    echo "${GPG_PRIVATE_KEY_1}${GPG_PRIVATE_KEY_2}${GPG_PRIVATE_KEY_3}" | base64 -d > "${GPG_SECRET_KEY_FILE}"
    gpg --allow-secret-key-import --import "${GPG_SECRET_KEY_FILE}"
    GPG_KEY_ID=$(gpg --allow-secret-key-import --import "${GPG_SECRET_KEY_FILE}" 2>&1 | grep -m 1 -oE "[A-F0-9]{16}")

    if [[ -z "${GPG_KEY_ID}" ]]; then
      echo Could not find GPG key ID.
      exit 1
    fi
    git config --global gpg.program gpg
    git config --global commit.gpgsign true
    git config user.signingkey "${GPG_KEY_ID}"
    git config --global user.email "${GITHUB_API_EMAIL}"
    git config --global user.name "${GITHUB_API_USER}"
    git config --global credential.UseHttpPath true
    exit 0
  fi
}

main() {
  set -e
  import_gpg_key
}

# ===================== #
# Calling main function #
# ===================== #
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi

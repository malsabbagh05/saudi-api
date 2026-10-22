#!/usr/bin/env bash
# Installs the pinned Trivy into $RUNNER_TEMP. No Trivy action: its tags were replaced
# with credential-stealing code in March 2026. The SHA-256 is the one the release lists
# for trivy_<version>_Linux-64bit.tar.gz. Change the version and the checksum together.
set -euo pipefail
version=0.74.0
sha256=2ae6fe3ee734b7fdf11335663e18c75ea12dccc76062f09f164a3b0f8be4371a
archive="$RUNNER_TEMP/trivy_${version}_Linux-64bit.tar.gz"
curl --fail --silent --show-error --location --retry 3 --output "$archive" \
  "https://github.com/aquasecurity/trivy/releases/download/v${version}/trivy_${version}_Linux-64bit.tar.gz"
echo "$sha256  $archive" | sha256sum --check --quiet
tar -xzf "$archive" -C "$RUNNER_TEMP" trivy

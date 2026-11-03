#!/bin/bash
# Requires a Rust toolchain with x86_64-unknown-linux-musl installed.
set -euo pipefail
repo=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo"
cargo build --manifest-path web/server-rs/Cargo.toml --locked -p egyuttparkolas-server --profile ci --target x86_64-unknown-linux-musl
package="$repo/out/portable/Egyuttparkolas-Server-Linux"
mkdir -p "$package"
cp web/server-rs/target/x86_64-unknown-linux-musl/ci/egyuttparkolas-server "$package/"
cp desktop/linux-server/{Dockerfile,compose.yaml,server.example.json,start.sh,.dockerignore,README.txt} "$package/"
cp LICENSE "$package/LICENSE.txt"
chmod 755 "$package/start.sh" "$package/egyuttparkolas-server"
(cd "$package" && sha256sum egyuttparkolas-server > SHA256SUMS)
tar -czf out/portable/Egyuttparkolas-Server-Linux.tar.gz -C out/portable Egyuttparkolas-Server-Linux
echo "Package: out/portable/Egyuttparkolas-Server-Linux.tar.gz"

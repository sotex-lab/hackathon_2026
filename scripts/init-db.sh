#!/usr/bin/env bash

set -euo pipefail

SQLPACKAGE="${SQLPACKAGE_PATH:-$(command -v sqlpackage || true)}"

if [ ! -x "$SQLPACKAGE" ]; then
  echo "SqlPackage was not found in the init image." >&2
  exit 1
fi

host="${SQLSERVER_HOST:-db}"
port="${SQLSERVER_PORT:-1433}"
user="${SQLSERVER_USER:-sa}"
password="${SQLSERVER_PASSWORD:-SotexSolutions123!}"
database="${TARGET_DATABASE:-SotexHackathon}"
bacpac_url="${BACPAC_URL:-https://sotex-hackathon-851725191980-eu-central-1-an.s3.eu-central-1.amazonaws.com/SotexHackathon.bacpac}"
bacpac_dir="${BACPAC_DIR:-/bacpac}"
bacpac_file="${bacpac_dir}/$(basename "${bacpac_url}")"

echo "Waiting for SQL Server at ${host}:${port}..."
for _ in $(seq 1 60); do
  if (echo >"/dev/tcp/${host}/${port}") >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! (echo >"/dev/tcp/${host}/${port}") >/dev/null 2>&1; then
  echo "SQL Server did not become ready in time." >&2
  exit 1
fi

mkdir -p "${bacpac_dir}"

if [ ! -f "${bacpac_file}" ]; then
  echo "Downloading bacpac from '${bacpac_url}' to '${bacpac_file}'."
  wget -O "${bacpac_file}" "${bacpac_url}"
else
  echo "Using cached bacpac '${bacpac_file}'."
fi

echo "Importing '${database}' from '${bacpac_file}'."
import_output="$("$SQLPACKAGE" \
  /Action:Import \
  /SourceFile:"${bacpac_file}" \
  /TargetServerName:"${host},${port}" \
  /TargetDatabaseName:"${database}" \
  /TargetUser:"${user}" \
  /TargetPassword:"${password}" \
  /TargetEncryptConnection:False \
  /TargetTrustServerCertificate:True 2>&1)" || import_status=$?

if [ "${import_status:-0}" -ne 0 ]; then
  if printf '%s\n' "$import_output" | grep -qi "already exists"; then
    echo "Database '${database}' already exists. Nothing to do."
    exit 0
  fi

  printf '%s\n' "$import_output" >&2
  exit "${import_status}"
fi

printf '%s\n' "$import_output"
echo "Import completed."

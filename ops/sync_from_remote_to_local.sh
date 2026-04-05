#!/bin/sh
set -eu

: "${SYNC_REMOTE:?Please set SYNC_REMOTE}"
: "${REMOTE_PATH:?Please set REMOTE_PATH}"
: "${LOCAL_DEST:?Please set LOCAL_DEST}"

mkdir -p "${LOCAL_DEST}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] syncing ${SYNC_REMOTE}:${REMOTE_PATH} -> ${LOCAL_DEST}"

rsync -avz \
  --progress \
  --stats \
  --partial \
  --delete \
  -e ssh \
  "${SYNC_REMOTE}:${REMOTE_PATH}" \
  "${LOCAL_DEST}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] done"

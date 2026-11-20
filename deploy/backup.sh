#!/usr/bin/env bash
# Nightly database backup. Keeps 14 days locally; also copies to S3 if
# BACKUP_BUCKET is set and the instance has an IAM role allowed to write there.
#
# Install (on the server):   crontab -e
#   30 2 * * * cd /home/ec2-user/Dangote-Refinery-ROI-Predictor && bash deploy/backup.sh >> backups/backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

mkdir -p backups
file="backups/roi-$(date -u +%Y%m%d-%H%M).sql.gz"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$file"
echo "$(date -u) wrote $file"

if [ -n "${BACKUP_BUCKET:-}" ]; then
  aws s3 cp "$file" "s3://$BACKUP_BUCKET/$(basename "$file")"
fi
find backups -name 'roi-*.sql.gz' -mtime +14 -delete

#!/usr/bin/env bash
# update.sh: pull the latest version, merge new config keys, smoke test, restart.
set -e
cd "$(dirname "$0")"

echo "Pulling latest version..."
git pull

# Add any new config keys from the example that config.json doesn't have yet.
python3 - <<'EOF'
import json

with open("config.json") as f:
    cfg = json.load(f)
with open("config.example.json") as f:
    ex = json.load(f)

def merge(dst, src, prefix=""):
    added = []
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
            added.append(prefix + k)
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            added += merge(dst[k], v, prefix + k + ".")
    return added

added = merge(cfg, ex)
if added:
    with open("config.json", "w") as f:
        json.dump(cfg, f, indent=2)
    print("Added new config keys with defaults:", ", ".join(added))
EOF

# Smoke test before restarting, so a bad pull never kills a running bot.
echo "Smoke test (--dry-run)..."
python3 bot.py --dry-run > /dev/null

./stop.sh 2>/dev/null || true
./start.sh
echo "Updated and restarted."

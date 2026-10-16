#!/bin/sh
# Scheduled refresh (cron / GitHub Actions): fetch real data, then rebuild static site.
set -e; cd "$(dirname "$0")"; python3 fetch.py && python3 build.py

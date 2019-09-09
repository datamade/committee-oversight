#!/bin/bash
set -e

psql -U postgres -c "CREATE DATABASE hearings"
psql -U postgres -d hearings -c "CREATE EXTENSION IF NOT EXISTS postgis"
# Add any more database initialization commands you may need here

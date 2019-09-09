#!/bin/bash
set -euo pipefail

# Make directory for project
mkdir -p /home/datamade/committee-oversight

apt-get update
apt-get install -y gnupg2
cd /opt/codedeploy-agent/deployment-root/$DEPLOYMENT_GROUP_ID/$DEPLOYMENT_ID/deployment-archive/ && chown -R datamade.datamade . && sudo -H -u datamade GPG=gpg2 blackbox_postdeploy

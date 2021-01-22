#!/bin/bash
set -euo pipefail
set -x

project_dir="/home/datamade/committee-oversight-$DEPLOYMENT_ID"

# Re-read supervisor config, add new processes and signal old processes
supervisorctl reread
supervisorctl add committee-oversight-$DEPLOYMENT_ID

# Check to see if our /pong/ endpoint responds with the correct deployment ID
loop_counter=0
while true; do
  if [[ -e /tmp/committee-oversight-${DEPLOYMENT_ID}.sock ]]; then
    running_app=`printf "GET /pong/ HTTP/1.1 \r\nHost: localhost \r\n\r\n" | nc -U /tmp/committee-oversight-$DEPLOYMENT_ID.sock | grep "$DEPLOYMENT_ID"`
    if [[ $running_app == $DEPLOYMENT_ID ]] ; then
      echo "App matching $DEPLOYMENT_ID started"
      break
    elif [[ $loop_counter -ge 20 ]]; then
      echo "Application matching deployment $DEPLOYMENT_ID has failed to start"
      exit 99
    else
      echo "Waiting for app $DEPLOYMENT_ID to start"
      sleep 1
    fi
  elif [[ $loop_counter -ge 20 ]]; then
    echo "Application matching deployment $DEPLOYMENT_ID has failed to start"
    exit 99
  else
    echo "Waiting for socket committee-oversight-$DEPLOYMENT_ID.sock to be created"
    sleep 1
  fi
  loop_counter=$(expr $loop_counter + 1)
done

# If everything is OK, reload nginx
echo "Reloading nginx"
service nginx configtest
service nginx reload || service nginx start

# It's safe to terminate the older version of the site
# by sending the TERM signal to old gunicorn processes.
# This code block iterates over deployments for a particular deployment group,
# checks each status (is it "RUNNING"?), and terminates the old, running deployment.
old_deployments=`(ls /opt/codedeploy-agent/deployment-root/$DEPLOYMENT_GROUP_ID | grep -Po "d-[A-Z0-9]{9}") || echo ''`
for deployment in $old_deployments; do
    if [[ ! $deployment == $DEPLOYMENT_ID ]]; then
        echo "Signalling application processes from $deployment"

        STATUS=`supervisorctl status committee-oversight-$deployment:*`
        if [[ $STATUS == *"RUNNING"* ]]; then
            supervisorctl signal TERM committee-oversight-$deployment:*
        fi
    fi
done;

# Send TERM signal to old gunicorn processes
old_deployments=`ls /opt/codedeploy-agent/deployment-root/$DEPLOYMENT_GROUP_ID | grep -Po 'd-[A-Z0-9]{9}'`
for deployment in $old_deployments; do
  if [[ ! $deployment == $DEPLOYMENT_ID ]]; then
    echo "Signalling application processes from $deployment"
    supervisorctl signal TERM committee-oversight-$deployment:*
  fi
done;

# Cleanup all versions except the most recent 10
old_versions=`find /home/datamade -maxdepth 1 -type d -printf '%TY-%Tm-%Td %TT %p\n' | sort | grep -Po '/home/datamade/committee-oversight-d-[A-Z0-9]{9}' | head -n -10`
for version in $old_versions; do
  echo "Removing $version"
  rm -rf $version
done;

# Cleanup virtualenvs except the most recent 10
old_venvs=`find /home/datamade/.virtualenvs -maxdepth 1 -type d -printf '%TY-%Tm-%Td %TT %p\n' | sort | grep -Po '/home/datamade/\.virtualenvs/committee-oversight-d-[A-Z0-9]{9}' | head -n -10`
for venv in $old_venvs; do
  echo "Removing $venv"
  rm -rf $venv
done;

# Remove old processes from supervisor
old_procs=`supervisorctl status | grep -P '(EXITED|STOPPED)' | grep -Po 'committee-oversight-d-[A-Z0-9]{9}'`
for proc in $old_procs; do
  echo "Removing $proc"
  supervisorctl remove $proc
done;

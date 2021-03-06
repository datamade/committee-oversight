#!/bin/bash
set -euo pipefail
set -x

project_dir="/home/datamade/committee-oversight-$DEPLOYMENT_ID"
venv_dir="/home/datamade/.virtualenvs/committee-oversight-$DEPLOYMENT_ID"

mkdir -p /home/datamade/.virtualenvs/committee-oversight
mv /home/datamade/committee-oversight /home/datamade/committee-oversight-$DEPLOYMENT_ID

python3 -m venv $venv_dir

chown -R datamade.www-data $project_dir
chown -R datamade.www-data $venv_dir

sudo -H -u datamade $venv_dir/bin/pip install --upgrade pip
sudo -H -u datamade $venv_dir/bin/pip install --upgrade setuptools
sudo -H -u datamade $venv_dir/bin/pip install -r $project_dir/requirements.txt --upgrade

mv $project_dir/configs/local_settings.py.$DEPLOYMENT_GROUP_NAME $project_dir/committeeoversight/local_settings.py && chown datamade.www-data $project_dir/committeeoversight/local_settings.py

psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'hearings'" | grep -q 1 || psql -U postgres -c "CREATE DATABASE hearings"
psql -U postgres -d hearings -c "CREATE EXTENSION IF NOT EXISTS postgis"
$venv_dir/bin/python $project_dir/manage.py migrate
$venv_dir/bin/python $project_dir/manage.py createcachetable
$venv_dir/bin/python $project_dir/manage.py collectstatic --no-input

# Configure the media folder for user uploads
media_dir=/home/datamade/media
ls $media_dir || (mkdir -p $media_dir && chown -R datamade.www-data $media_dir)
chmod -R g+r $media_dir

# Assign variables based on deployment group
if [ "$DEPLOYMENT_GROUP_NAME" == "staging" ]; then
    export DOMAIN="committeeoversight.datamade.us"
fi

if [ "$DEPLOYMENT_GROUP_NAME" == "production" ]; then
    export DOMAIN="oversight-index.thelugarcenter.org"
fi

# Echo a simple nginx configuration into the correct place, and tell
# certbot to request a cert if one does not already exist.
if [ ! -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem ]; then
    echo "server {
        listen 80;
        server_name $DOMAIN;
        location ~ .well-known/acme-challenge {
            root /usr/share/nginx/html;
            default_type text/plain;
        }
    }" > /etc/nginx/conf.d/committee-oversight.conf
    service nginx reload
    certbot -n --nginx -d $DOMAIN -m devops@datamade.us --agree-tos
fi

$venv_dir/bin/python $project_dir/scripts/render_configs.py $DEPLOYMENT_ID $DEPLOYMENT_GROUP_NAME

# Assign correct ownership and permissions to the crontask and log file
if [ "$DEPLOYMENT_GROUP_NAME" == "production" ]; then
  chown root.root /etc/cron.d/committee-oversight-crontasks
  sudo touch /tmp/committee-oversight-crontasks-backups.log
  sudo touch /tmp/committee-oversight-crontasks-ratings.log
  sudo chown datamade.www-data /tmp/committee-oversight-crontasks-backups.log
  sudo chown datamade.www-data /tmp/committee-oversight-crontasks-ratings.log
  chmod 644 /etc/cron.d/committee-oversight-crontasks
fi

echo "DEPLOYMENT_ID='$DEPLOYMENT_ID'" > $project_dir/committeeoversightapp/deployment.py

#!/bin/bash
set -euo pipefail

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

cd $project_dir && sudo -H -u datamade blackbox_postdeploy
mv $project_dir/configs/local_settings.$DEPLOYMENT_GROUP_NAME.py $project_dir/committeeoversight/local_settings.py && chown datamade.www-data $project_dir/depaul_ihs_site/local_settings.py

psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'hearings'" | grep -q 1 || psql -U postgres -c "CREATE DATABASE hearings"
psql -U postgres -d hearings -c "CREATE EXTENSION IF NOT EXISTS postgis"
$venv_dir/bin/python $project_dir/manage.py migrate
$venv_dir/bin/python $project_dir/manage.py collectstatic --no-input

# Assign variables based on deployment group
if [ "$DEPLOYMENT_GROUP_NAME" == "staging" ]; then
    export DOMAIN="committeeoversight.datamade.us"
fi

if [ "$DEPLOYMENT_GROUP_NAME" == "production" ]; then
    export DOMAIN="committeeoversight.datamade.us"
fi

# Generate SSL cert if one does not exist
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
    certbot --nginx -d $DOMAIN
fi

$venv_dir/bin/python $project_dir/scripts/render_configs.py $DEPLOYMENT_ID $DEPLOYMENT_GROUP_NAME

echo "DEPLOYMENT_ID='$DEPLOYMENT_ID'" > $project_dir/committeeoversightapp/deployment.py

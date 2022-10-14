#!/bin/bash
cd ~/
sudo cp ruqqus/nginx.txt /etc/nginx/sites-available/ruqqus.com.conf
sudo nginx -s reload
. ~/venv/bin/activate
. ~/env.sh
cd ~/ruqqus
pip3 install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:~/ruqqus
cd ~/
#echo "starting background worker"
#python ruqqus/scripts/recomputes.py 
#echo "starting regular workers"
#NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program gunicorn ruqqus.__main__:app -k gevent -w $WEB_CONCURRENCY --worker-connections $WORKER_CONNECTIONS --max-requests 10000 --max-requests-jitter 500 --preload --bind 127.0.0.1:5000 -D #--log-level debug --log-file log.txt
echo "starting chat worker"
gunicorn ruqqus.__main__:app load_chat -k eventlet  -w 1 --worker-connections 1000 --max-requests 100000 --preload --bind 127.0.0.1:5001
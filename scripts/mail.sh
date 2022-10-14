#!/bin/sh
cd ~/
source venv/bin/activate
source env.sh
cd ~/ruqqus/scripts
export PYTHONPATH=$PYTHONPATH:~/ruqqus
export CACHE_TYPE=filesystem
python mailing_list.py
deactivate
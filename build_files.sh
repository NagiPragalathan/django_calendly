#!/bin/bash
chmod +x build_files.sh
echo "starting install..."
python3.12 -m pip install gridfs
python3.12 -m pip install -r requirements.txt
python3.12 manage.py collectstatic --noinput
echo "end install-----------------------"
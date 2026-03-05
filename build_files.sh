#!/bin/bash
chmod +x build_files.sh
echo "starting install..."
python3 -m pip install -r requirements.txt --break-system-packages
python3 manage.py collectstatic --noinput
echo "end install-----------------------"
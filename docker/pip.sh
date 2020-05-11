#!/bin/bash
cp -r /root/keys /root/.ssh
# chown root:root /root/.ssh/config /root/.ssh/id_rsa
pip install -e .
tail -f /dev/null
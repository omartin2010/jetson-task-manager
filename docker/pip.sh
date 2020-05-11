#!/bin/bash
cp -r /root/keys /root/.ssh
pip install -e .
tail -f /dev/null
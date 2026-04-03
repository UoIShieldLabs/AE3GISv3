#!/bin/sh
# PLC initialization script
# This script runs when a PLC container starts

echo "PLC initialized at $(date)"
touch /opt/rand.txt
echo "Random data generated at $(date)" > /opt/rand.txt
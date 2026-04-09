#!/bin/bash

USER="root"
PASS="root"

echo "Scanning router for exposed services..."
nmap -sV -O --script=vuln 192.168.2.1 -T5

echo "SSH is open, attempting to connect..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@192.168.2.1 "ip route" > ~/routes.txt
echo "Routes saved to routes.txt"
echo "------------------------------"
echo "Contents of routes.txt:"
cat ~/routes.txt


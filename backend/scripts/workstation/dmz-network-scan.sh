#!/bin/bash

echo "Nmaping hosts on the DMZ network..."
echo "Using routes from ~/routes.txt"
cat ~/routes.txt

nmap -sV -O --script=vuln 192.168.3.5 -T5
echo "Scan complete. Check the output above for open vulnerable services on the DMZ network."


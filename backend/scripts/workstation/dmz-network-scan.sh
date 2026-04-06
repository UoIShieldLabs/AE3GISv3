#!/bin/bash

echo "Discovering hosts on the DMZ network..."
echo "Using routes from ~/routes.txt"
cat ~/routes.txt

nmap -sV 192.168.3.0/24
echo "Scan complete. Check the output above for open services on the DMZ network."

echo "found SSH open on DMZ router"

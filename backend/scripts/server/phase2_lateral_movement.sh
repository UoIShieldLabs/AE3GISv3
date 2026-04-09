#!/bin/sh
# Phase 2: Lateral Movement — IT-fileserv compromise
# Simulates worm spread from IT-ws-1 to the file server via network share.
# Starts a C2 relay listener on port 4444 — after this runs, the Phase 1
# beacon on IT-ws-1 will see its connections succeed (SYN→RST becomes TCP handshake).

echo "=== Phase 2: Lateral Movement ==="
echo "Target: IT File Server (IT-fileserv, 10.0.1.50)"
echo "Time:   $(date -u +%Y-%m-%dT%H:%M:%S)"

# Worm spread marker on the shared file store
mkdir -p /srv/files/.stuxnet
echo "INFECTED=$(date -u +%Y-%m-%dT%H:%M:%S) SOURCE=IT-ws-1 VECTOR=network_share SHARE=\\\\fileserv\\IT-Data" > /srv/files/.infected

# Stolen credentials harvested via C2 channel from IT-ws-1
cat > /tmp/stolen_creds.txt << 'EOF'
; Credentials harvested from IT-ws-1 via C2 relay (LSASS dump + browser store)
; Format: username:domain:LM_hash:NTLM_hash
engineer1:FACILITY:aad3b435b51404eeaad3b435b51404ee:8846f7eaee8fb117ad06bdd830b7586c
admin:FACILITY:aad3b435b51404eeaad3b435b51404ee:f4dcf4b06ad2d3dc6f95dea9fd5a9c4a
svc_historian:FACILITY:aad3b435b51404eeaad3b435b51404ee:2b5760d5e30c72f03c7a4a7a29ab5cf0
scada_admin:SCADA:aad3b435b51404eeaad3b435b51404ee:a87f3a337d73085c45f9416be5787d86
EOF

# Persistence artifact (cron file — artifact only, not an active cron)
cat > /etc/cron.d/stuxnet_persist << 'EOF'
# Stuxnet persistence mechanism
# Reinstalls payload if removed; survives reboot via cron
*/5 * * * * root /tmp/.stuxnet/payload.bin --reinstall 2>/dev/null
EOF

echo ""
echo "Lateral movement artifacts:"
ls -la /srv/files/
echo ""
echo "Stolen credentials: /tmp/stolen_creds.txt"
echo "Persistence cron:   /etc/cron.d/stuxnet_persist"

# Stop any existing C2 listener
pkill -f "nc -l" 2>/dev/null || true
sleep 1

# C2 relay listener on port 4444
# Once this starts, IT-ws-1 beacon connections succeed — visible on Wireshark
# as a full TCP handshake instead of SYN→RST
(
  while true; do
    nc -l -p 4444 2>/dev/null
  done
) &

LISTENER_PID=$!
mkdir -p /tmp/.stuxnet
echo $LISTENER_PID > /tmp/.stuxnet/listener.pid
echo ""
echo "C2 relay listener started on :4444 (PID $LISTENER_PID)"
echo "IT-ws-1 beacon connections will now succeed — check Wireshark on IT-switch"
echo ""
echo "IOC hunting: ps aux | grep nc  |  cat /tmp/stolen_creds.txt  |  ls /srv/files/"

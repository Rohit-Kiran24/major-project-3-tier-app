#!/bin/bash
# =============================================================================
# NAT Instance Bootstrap (Amazon Linux 2023)
#
# Turns a plain EC2 instance into a NAT router so private-subnet instances can
# reach the internet (Docker Hub pulls, dnf updates, AWS API calls) without
# being publicly reachable themselves.
#
# Rendered into aws_instance.nat user_data by the VPC module.
# =============================================================================

set -uxo pipefail
exec > >(tee -a /var/log/nat-bootstrap.log) 2>&1

echo "$(date) - NAT bootstrap starting"

# ---------- Enable IPv4 forwarding (persisted across reboots) ----------
echo "net.ipv4.ip_forward = 1" >/etc/sysctl.d/99-nat.conf
sysctl -w net.ipv4.ip_forward=1

# ---------- Install iptables ----------
# AL2023 uses nftables; iptables-nft provides the iptables CLI on top of it.
dnf install -y iptables-nft || dnf install -y iptables || true

# ---------- NAT rule script (re-applied on every boot) ----------
# The primary NIC name depends on the hypervisor generation:
#   Xen   (t2.*)            -> eth0
#   Nitro (t3/t4g/m5/c5...) -> enX0 or ens5
# Hardcoding either one breaks the other, so detect it from the default route.
cat >/usr/local/sbin/configure-nat.sh <<'SCRIPT'
#!/bin/bash
set -eux
PRIMARY_IF=$(ip -o -4 route show to default | awk '{print $5}' | head -n1)
[ -n "$PRIMARY_IF" ] || { echo "could not detect primary interface"; exit 1; }

# -C tests for an existing rule so re-runs stay idempotent.
iptables -t nat -C POSTROUTING -o "$PRIMARY_IF" -j MASQUERADE 2>/dev/null ||
  iptables -t nat -A POSTROUTING -o "$PRIMARY_IF" -j MASQUERADE

iptables -P FORWARD ACCEPT
echo "NAT configured on $PRIMARY_IF"
SCRIPT
chmod +x /usr/local/sbin/configure-nat.sh

# ---------- Re-apply at boot via systemd ----------
cat >/etc/systemd/system/configure-nat.service <<'UNIT'
[Unit]
Description=Configure NAT masquerading for private subnets
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/configure-nat.sh

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now configure-nat.service

echo "$(date) - NAT bootstrap finished"

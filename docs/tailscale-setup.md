# Tailscale Setup — Raspberry Pi 3 Model A+ (`autism-pi`)

## Prerequisites

- Pi is on the local network and reachable via SSH
- A Tailscale account at [tailscale.com](https://tailscale.com)
- Pi is running Raspberry Pi OS (Debian-based, ARM)

---

## 1. Install Tailscale

SSH into the pi:

```bash
ssh tyler@autism-pi
```

Run the official Tailscale install script for Debian/ARM:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

This script detects the OS and architecture automatically and adds the Tailscale apt repository, installs `tailscaled`, and starts the service.

### Pi 3 Specific Note: iptables/nftables Compatibility

Raspberry Pi OS Bullseye and later default to `nftables`, but older kernels (like the one on the Pi 3) may have issues. If `tailscale up` hangs or networking breaks, force the legacy iptables backend:

```bash
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
```

Then restart the Tailscale daemon:

```bash
sudo systemctl restart tailscaled
```

---

## 2. Authenticate the Pi

Run:

```bash
sudo tailscale up
```

This prints an authentication URL. Open it in a browser on any device, log into your Tailscale account, and authorize the pi. The terminal will confirm once authenticated.

To set the pi's Tailscale hostname at the same time (see also step 6):

```bash
sudo tailscale up --hostname=autism-pi
```

---

## 3. Verify the Pi Appears in the Admin Console

1. Go to [login.tailscale.com/admin/machines](https://login.tailscale.com/admin/machines)
2. Confirm `autism-pi` (or whatever hostname was assigned) appears in the machine list
3. Note the Tailscale IP — it will be in the `100.x.x.x` range (CGNAT space)

You can also check from the pi itself:

```bash
tailscale ip -4
```

---

## 4. SSH into the Pi via Tailscale from Any Network

Once the pi is authenticated and both devices are on the same Tailscale network, SSH works over the Tailscale IP or MagicDNS hostname from anywhere.

**Using the Tailscale IP:**

```bash
ssh tyler@100.x.x.x
```

Replace `100.x.x.x` with the IP shown in the admin console or from `tailscale ip -4`.

**Using MagicDNS (if enabled on your Tailnet):**

```bash
ssh tyler@autism-pi
```

MagicDNS is enabled by default for new Tailnets. If it is not resolving, enable it at [login.tailscale.com/admin/dns](https://login.tailscale.com/admin/dns) under the "MagicDNS" toggle.

---

## 5. Enable Tailscale to Start on Boot

The install script typically enables `tailscaled` automatically, but confirm and set it explicitly:

```bash
sudo systemctl enable tailscaled
sudo systemctl start tailscaled
```

Verify the service is running and enabled:

```bash
sudo systemctl status tailscaled
```

After a reboot, the pi should reconnect to Tailscale automatically without any manual intervention.

---

## 6. Set a Recognizable Tailscale Hostname (Optional)

By default Tailscale uses the system hostname. The pi's hostname is already `autism-pi`, so it should appear that way in the admin console. To explicitly set or change it:

```bash
sudo tailscale up --hostname=autism-pi
```

This can be re-run at any time without re-authenticating. The new hostname appears in the admin console within a few seconds.

To also set the system hostname to match (if it is not already set):

```bash
sudo hostnamectl set-hostname autism-pi
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Install Tailscale | `curl -fsSL https://tailscale.com/install.sh \| sh` |
| Authenticate | `sudo tailscale up --hostname=autism-pi` |
| Check Tailscale IP | `tailscale ip -4` |
| Check status | `tailscale status` |
| Enable on boot | `sudo systemctl enable tailscaled` |
| SSH via Tailscale IP | `ssh tyler@100.x.x.x` |
| SSH via MagicDNS | `ssh tyler@autism-pi` |

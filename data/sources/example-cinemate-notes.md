# Example Cinemate Notes

This is placeholder documentation so the starter project can be tested immediately. Replace it with the real Cinemate and cinepi-raw docs.

## cinepi.local does not resolve

If `cinepi.local` works on some devices but not others, the likely issue is local network name resolution. Some devices support mDNS/Bonjour out of the box, while others may not. Try connecting to the Raspberry Pi by IP address. Also verify that Avahi is installed and running on the Pi.

Useful checks:

```bash
hostname -I
systemctl status avahi-daemon
ping cinepi.local
```

Router client isolation, guest networks, VPN clients, or firewall rules can also prevent discovery.

## Redis connection errors

Cinemate and cinepi-raw workflows often rely on Redis for control messages. If the UI cannot control the recorder, verify that Redis is running and listening locally.

```bash
systemctl status redis-server
redis-cli ping
```

`PONG` means Redis is responding.

## SSD not mounted

If recordings cannot be written, verify that the media drive is mounted before starting Cinemate. Check `lsblk`, `df -h`, and the expected recording path. If a service starts before the drive is mounted, delay the service or add an explicit mount dependency.

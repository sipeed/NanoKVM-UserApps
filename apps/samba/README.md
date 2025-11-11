# Samba File Sharing Service

This is a Samba file sharing management application for NanoKVM.

## Features

- One-click Samba installation
- Start/Stop Samba service

## Share Configuration

After installation, a share named `kvm` will be automatically created:
- Share path: `/data`
- Default user: `root`
- Default password: `sipeed`

## Important Security Notice

**For the security of your system, please perform the following operations immediately after installation:**

### 1. Change Default Password

The default password `sipeed` is very insecure. Change it immediately:

```bash
# Execute after SSH login to the device
smbpasswd root
```

### 2. (Recommended) Create Dedicated Samba User

It's not recommended to use the root user to access Samba shares. Create a dedicated user instead:

```bash
# Create a new system user
useradd -M -s /usr/sbin/nologin sambauser

# Set Samba password for this user
smbpasswd -a sambauser

# Edit /etc/samba/smb.conf, change "valid users = root" to "valid users = sambauser"
vim /etc/samba/smb.conf

# Restart Samba services
systemctl restart smbd nmbd
```

### 3. (Optional) Disable Root User Samba Access

If you have created a dedicated user, you can disable root:

```bash
smbpasswd -d root
```

## Accessing the Share

### Windows

1. Open File Explorer
2. Enter in the address bar: `\\<device_IP_address>\kvm`
3. Enter username and password

### macOS

1. In Finder, select "Go" > "Connect to Server"
2. Enter: `smb://<device_IP_address>/kvm`
3. Enter username and password

### Linux

```bash
smb://<device_IP_address>/kvm
```

## Service Management

Via touchscreen or key:
- **Start**: Start Samba service
- **Stop**: Stop Samba service
- **Exit button**: Exit application

## Configuration Files

- Samba configuration: `/etc/samba/smb.conf`

## Uninstallation

To uninstall Samba:

```bash
sudo systemctl stop smbd nmbd wsdd2
sudo systemctl disable smbd nmbd wsdd2
sudo apt remove --purge samba wsdd2
```

---

**Reminder**: Please be sure to change the default password to ensure system security!

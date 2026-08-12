# smb-monitor
smb-monitor is a service to monitor changes made in shared folders.

It reads files in samba audit format, stores all information in a database and sends warning emails 
on excessive deletes (unlinkat) or excessive moves (renameat, where the only change is the path but 
not the node's name)

The Linux Server is inside the Linux Server directory.  
To enable it to run as a service (in Ubuntu), you must create a file 
/etc/systemd/system/smb-monitor.service
with the following content:

```
[Unit]
Description=SMB monitor service
After=multi-user.target
[Service]
User=root
Type=simple
WorkingDirectory=/home/user/smb-monitor
ExecStart=/usr/bin/python3 /home/user/smb-monitor/main.py
Restart=on-failure
RestartSec=42s
KillSignal=SIGINT
[Install]
WantedBy=multi-user.target
```

Then, enable the service with:  
	sudo systemctl enable smb-monitor.service  
Start it with:  
	sudo systemctl start smb-monitor.service  
To check its status:  
	sudo systemctl status smb-monitor.service  
  
There is also a a Windows app that monitors directory activity and writes a file in the same style as a Samba Audit

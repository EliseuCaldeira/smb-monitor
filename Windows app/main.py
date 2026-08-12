####################################################################################################
# --windowed --log-level=WARN LEVEL may be one of TRACE, DEBUG, INFO, WARN, DEPRECATION, ERROR, FATAL (default: INFO)
# 
# pyinstaller --log-level=WARN --icon favicon.ico --onefile --add-data="include_this_folder:include_this_folder" main.py --name smb-monitor
# 
# pyinstaller --log-level=WARN --icon favicon.ico --onefile main.py --name smb-monitor
# 
# import include_this_folder.test
# 
####################################################################################################

# Imports:
import time
import datetime
import os
import sys
import tomllib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Global variables:
CONFIG_FILE = r"./config.ini"

if not os.path.exists(CONFIG_FILE):
	print(f"Error: configuration file ({CONFIG_FILE}) not found!")
	time.sleep(2)
	sys.exit(1)

with open(CONFIG_FILE, 'rb') as f:
	config = tomllib.load(f)

if 'SERVER_HOSTNAME' not in config or not config['SERVER_HOSTNAME']:
	print(f"Error: SERVER_HOSTNAME is not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
SERVER_HOSTNAME = config['SERVER_HOSTNAME']

if 'LOG_FILE' not in config or not config['LOG_FILE']:
	print(f"Error: LOG_FILE is not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
LOG_FILE = config['LOG_FILE']

if 'USER_NAME' not in config or not config['USER_NAME']:
	USER_NAME = r"unknown.user"
else:
	USER_NAME = config['USER_NAME']

if 'USER_HOSTNAME' not in config or not config['USER_HOSTNAME']:
	USER_HOSTNAME = r"unknown-host"
else:
	USER_HOSTNAME = config['USER_HOSTNAME']

if 'USER_IP' not in config or not config['USER_IP']:
	USER_IP = r"0.0.0.0"
else:
	USER_IP = config['USER_IP']

if (
	'PURGE_AFTER' not in config
	or not isinstance(config['PURGE_AFTER'], int)
	or config['PURGE_AFTER'] < 0
	or config['PURGE_AFTER'] > 23
):
	PURGE_AFTER = 4
else:
	PURGE_AFTER = config['PURGE_AFTER']

if 'SHARES' not in config or not config['SHARES']:
	print(f"Error: SHARES are not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
SHARES = config['SHARES']

last_audit_purge = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
"""
Last time, in UTC, that the audits log file was flushed, ou purged
"""

current_time = datetime.datetime.now(datetime.timezone.utc)
"""
Holds current time in UTC
"""

current_local_time = datetime.datetime.now()
"""
Holds current local time
"""

del config

print(f"Settings imported from {CONFIG_FILE} :")
print(f"SERVER_HOSTNAME = {SERVER_HOSTNAME}")
print(f"LOG_FILE = {LOG_FILE}")
print(f"USER_NAME = {USER_NAME}")
print(f"USER_HOSTNAME = {USER_HOSTNAME}")
print(f"USER_IP = {USER_IP}")
print(f"PURGE_AFTER = {PURGE_AFTER}")
print("Shares:")
for key, value in SHARES.items():
	print(f"  {key}: {value[0]} -> {value[1]}")

# Classes:
class Watcher:

	def __init__(self, shares):
		self.shares = shares
		self.observers = []
	
	def run(self):
		global last_audit_purge
		global current_time
		global current_local_time

		for key, value in self.shares.items():
			observer = Observer()
			event_handler = Handler(value[0])
			observer.schedule(event_handler, value[1], recursive=True)
			observer.start()
			self.observers.append(observer)
	
		try:
			while True:
				current_time = datetime.datetime.now(datetime.timezone.utc)
				time_difference = current_time - last_audit_purge
				current_local_time = datetime.datetime.now()
				current_local_hour = current_local_time.hour
				if (
					current_local_hour >= PURGE_AFTER and
					current_local_hour <= PURGE_AFTER + 1 and
					time_difference.total_seconds() >= 22 * 3600 # 22 hours in seconds
				):
					with open(LOG_FILE, "w", encoding="utf-8") as file:
						pass
					last_audit_purge = datetime.datetime.now(datetime.timezone.utc)
				time.sleep(1)
		except KeyboardInterrupt:
			for observer in self.observers:
				observer.stop()
	
		for observer in self.observers:
			observer.join()

class Handler(FileSystemEventHandler):
	"""
	The Linux version only has Renameat, Mkdirat and Unlinkat (Move is inferred from a Renameat event)
	"""

	def __init__(self, share_name):
		self.share_name = share_name

	def on_moved(self, event):
		"""
		Logs when a file or directory is renamed
		"""
		log_line = (
			f"{time.strftime("%b %e %H:%M:%S")} "
			f"{SERVER_HOSTNAME} "
			f"smbd_audit: {USER_NAME}|{USER_IP}|{USER_HOSTNAME}|{self.share_name}|renameat|ok|"
			f"{event.src_path}|"
			f"{event.dest_path}"
		).replace('\\', '/')
		try:
			with open(LOG_FILE, "a", encoding="utf-8") as file:
				file.write(f"{log_line}\n")
		except:
			pass
		#print(log_line)
	
	def on_created(self, event):
		"""
		Logs when a directory is created
		"""
		if event.is_directory:
			log_line = (
				f"{time.strftime("%b %e %H:%M:%S")} "
				f"{SERVER_HOSTNAME} "
				f"smbd_audit: {USER_NAME}|{USER_IP}|{USER_HOSTNAME}|{self.share_name}|mkdirat|ok|"
				f"{event.src_path}"
			).replace('\\', '/')
			try:
				with open(LOG_FILE, "a", encoding="utf-8") as file:
					file.write(f"{log_line}\n")
			except:
				pass
			#print(log_line)
	
	def on_deleted(self, event):
		"""
		Logs when a file or directory is renamed
		"""
		log_line = (
			f"{time.strftime("%b %e %H:%M:%S")} "
			f"{SERVER_HOSTNAME} "
			f"smbd_audit: {USER_NAME}|{USER_IP}|{USER_HOSTNAME}|{self.share_name}|unlinkat|ok|"
			f"{event.src_path}"
		).replace('\\', '/')
		try:
			with open(LOG_FILE, "a", encoding="utf-8") as file:
				file.write(f"{log_line}\n")
		except:
			pass
		#print(log_line)

	'''
	def on_modified(self, event):
		"""
		This only logs true file edits and is incompatible with what we already have (Linux version)
		Because it is incompatible with what we have, it'll be commented, for now.
		"""
		if not event.is_directory:
			log_line = (
				f"{time.strftime("%b %e %H:%M:%S")} "
				f"{SERVER_HOSTNAME} "
				f"smbd_audit: {USER_NAME}|{USER_IP}|{USER_HOSTNAME}|{SHARE_NAME}|edit|ok|"
				f"{event.src_path}"
			).replace('\\', '/')
			print(log_line)
	'''


# Main:
if __name__ == "__main__":
	Watcher(SHARES).run()
	print(f"Service is live and exporting results to {LOG_FILE} ...")

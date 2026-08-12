#!/usr/bin/env python3

################################################################################
# smb-monitor Linux server
################################################################################

# Imports:
try:
	import tomllib
except ModuleNotFoundError:
	import tomli as tomllib
import os
import time
import sys
import logging
from logging.handlers import RotatingFileHandler
from include.Service import Service


def return_int(value, default=0, minimum=0, maximum=65535):
	try:
		result = int(float(value))
	except (TypeError, ValueError):
		return default
	return max(minimum, min(result, maximum))


# Global variables:
CONFIG_FILE = r"./config.ini"

if not os.path.exists(CONFIG_FILE):
	print(f"Error: configuration file ({CONFIG_FILE}) not found!")
	time.sleep(2)
	sys.exit(1)

with open(CONFIG_FILE, 'rb') as f:
	config = tomllib.load(f)

if 'HTTP_PORT' not in config or not config['HTTP_PORT']:
	HTTP_PORT = 8080
else:
	HTTP_PORT = return_int(config['HTTP_PORT'], 8080)

if 'LOG_FILE' not in config or not config['LOG_FILE']:
	LOG_FILE = r"./smb-monitor.service.log"
else:
	LOG_FILE = config['LOG_FILE']

if 'DELAY' not in config or not config['DELAY']:
	DELAY = 5
else:
	DELAY = return_int(config['DELAY'], 5, 1, 30)

if 'EMAIL_BOX' not in config or not str(config['EMAIL_BOX']).strip():
	print(r"Error: EMAIL_BOX is not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
EMAIL_BOX = config['EMAIL_BOX']

if 'EMAIL_PASSWORD' not in config or not str(config['EMAIL_PASSWORD']).strip():
	print(r"Error: EMAIL_PASSWORD is not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
EMAIL_PASSWORD = config['EMAIL_PASSWORD']

if 'SMTP' not in config or not str(config['SMTP']).strip():
	print(r"Error: SMTP is not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
SMTP = config['SMTP']

if 'SMTP_PORT' not in config or not str(config['SMTP_PORT']).strip():
	print(r"Error: SMTP_PORT is not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
SMTP_PORT = return_int(config['SMTP_PORT'], 587, 1)

if 'EMAIL_RECIPIENT' not in config or not str(config['EMAIL_RECIPIENT']).strip():
	print(r"Error: EMAIL_RECIPIENT is not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
EMAIL_RECIPIENT = config['EMAIL_RECIPIENT']

if 'ZABBIX_SERVER_IP' not in config or not config['ZABBIX_SERVER_IP']:
	ZABBIX_SERVER_IP = None
else:
	ZABBIX_SERVER_IP = config['ZABBIX_SERVER_IP']

if 'ZABBIX_SERVER_PORT' not in config or not config['ZABBIX_SERVER_PORT']:
	ZABBIX_SERVER_PORT = 10051
else:
	ZABBIX_SERVER_PORT = return_int(config['ZABBIX_SERVER_PORT'], 10051)

if 'ZABBIX_THIS_HOST' not in config or not config['ZABBIX_THIS_HOST']:
	ZABBIX_THIS_HOST = None
else:
	ZABBIX_THIS_HOST = config['ZABBIX_THIS_HOST']

if 'EXCESSIVE_UNLINKS_THRESHOLD' not in config or not config['EXCESSIVE_UNLINKS_THRESHOLD']:
	EXCESSIVE_UNLINKS_THRESHOLD = 50
else:
	EXCESSIVE_UNLINKS_THRESHOLD = return_int(config['EXCESSIVE_UNLINKS_THRESHOLD'], 50, 1)

if 'EXCESSIVE_UNLINKS_TIME_WINDOW' not in config or not config['EXCESSIVE_UNLINKS_TIME_WINDOW']:
	EXCESSIVE_UNLINKS_TIME_WINDOW = 300
else:
	EXCESSIVE_UNLINKS_TIME_WINDOW = return_int(config['EXCESSIVE_UNLINKS_TIME_WINDOW'], 300, 1)

if 'EXCESSIVE_UNLINKS_COOLDOWN' not in config or not config['EXCESSIVE_UNLINKS_COOLDOWN']:
	EXCESSIVE_UNLINKS_COOLDOWN = 600
else:
	EXCESSIVE_UNLINKS_COOLDOWN = return_int(config['EXCESSIVE_UNLINKS_COOLDOWN'], 600, 1)

if 'EXCESSIVE_MOVES_THRESHOLD' not in config or not config['EXCESSIVE_MOVES_THRESHOLD']:
	EXCESSIVE_MOVES_THRESHOLD = 50
else:
	EXCESSIVE_MOVES_THRESHOLD = return_int(config['EXCESSIVE_MOVES_THRESHOLD'], 50, 1)

if 'EXCESSIVE_MOVES_TIME_WINDOW' not in config or not config['EXCESSIVE_MOVES_TIME_WINDOW']:
	EXCESSIVE_MOVES_TIME_WINDOW = 300
else:
	EXCESSIVE_MOVES_TIME_WINDOW = return_int(config['EXCESSIVE_MOVES_TIME_WINDOW'], 300, 1)

if 'EXCESSIVE_MOVES_COOLDOWN' not in config or not config['EXCESSIVE_MOVES_COOLDOWN']:
	EXCESSIVE_MOVES_COOLDOWN = 600
else:
	EXCESSIVE_MOVES_COOLDOWN = return_int(config['EXCESSIVE_MOVES_COOLDOWN'], 600, 1)

if 'AUDITS' not in config or not config['AUDITS']:
	print(r"Error: AUDITS are not set in the configuration file!")
	time.sleep(2)
	sys.exit(1)
AUDITS = config['AUDITS']

# Ensure each path prefix to ignore ends with a trailing slash
for key, value in AUDITS.items():
	if value[1]:
		value[1] = value[1].rstrip('/')
		value[1] = value[1] + '/'

del config

# Prepare logger:
log_formatter = logging.Formatter(
	fmt='%(asctime)s %(levelname)s %(filename)s(%(lineno)d)\n%(message)s\n',
	datefmt='%Y-%m-%d %H:%M:%S UTC/GMT %z'
)
log_file = LOG_FILE
my_handler = RotatingFileHandler(
	log_file,
	mode='a',
	maxBytes=100*1024, # 100KB
	backupCount=3,
	encoding='utf-8',
	delay=False
)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.DEBUG)#.WARNING)#.DEBUG)#.INFO)#
log = logging.getLogger('root')
log.setLevel(logging.DEBUG)#.WARNING)#.DEBUG)#.INFO)#
log.addHandler(my_handler)

# Log initial info:
initial_info = "..:: Service \"smb-monitor\" started ::..\n"
initial_info += f"Settings imported from {CONFIG_FILE} :\n"
initial_info += f"HTTP_PORT = {HTTP_PORT}\n"
initial_info += f"LOG_FILE = {LOG_FILE}\n"
initial_info += f"DELAY = {DELAY}\n"
initial_info += f"EMAIL_BOX = {EMAIL_BOX}\n"
initial_info += f"EMAIL_PASSWORD = ****\n"
initial_info += f"SMTP = {SMTP}\n"
initial_info += f"SMTP_PORT = {SMTP_PORT}\n"
initial_info += f"EMAIL_RECIPIENT = {EMAIL_RECIPIENT}\n"
initial_info += f"ZABBIX_SERVER_IP = {ZABBIX_SERVER_IP}\n"
initial_info += f"ZABBIX_SERVER_PORT = {ZABBIX_SERVER_PORT}\n"
initial_info += f"ZABBIX_THIS_HOST = {ZABBIX_THIS_HOST}\n"
initial_info += f"EXCESSIVE_UNLINKS_THRESHOLD = {EXCESSIVE_UNLINKS_THRESHOLD}\n"
initial_info += f"EXCESSIVE_UNLINKS_TIME_WINDOW = {EXCESSIVE_UNLINKS_TIME_WINDOW}\n"
initial_info += f"EXCESSIVE_UNLINKS_COOLDOWN = {EXCESSIVE_UNLINKS_COOLDOWN}\n"
initial_info += f"EXCESSIVE_MOVES_THRESHOLD = {EXCESSIVE_MOVES_THRESHOLD}\n"
initial_info += f"EXCESSIVE_MOVES_TIME_WINDOW = {EXCESSIVE_MOVES_TIME_WINDOW}\n"
initial_info += f"EXCESSIVE_MOVES_COOLDOWN = {EXCESSIVE_MOVES_COOLDOWN}\n"
initial_info += "AUDITS:"
for key, value in AUDITS.items():
	initial_info += f"\n	{key}: {value[0]} | {value[1]} | {value[2]}"

log.info(initial_info)
del initial_info

service = Service(
	AUDITS,
	DELAY,
	HTTP_PORT,
	EMAIL_BOX,
	EMAIL_PASSWORD,
	SMTP,
	SMTP_PORT,
	EMAIL_RECIPIENT,
	ZABBIX_SERVER_IP,
	ZABBIX_SERVER_PORT,
	ZABBIX_THIS_HOST,
	EXCESSIVE_UNLINKS_THRESHOLD,
	EXCESSIVE_UNLINKS_TIME_WINDOW,
	EXCESSIVE_UNLINKS_COOLDOWN,
	EXCESSIVE_MOVES_THRESHOLD,
	EXCESSIVE_MOVES_TIME_WINDOW,
	EXCESSIVE_MOVES_COOLDOWN
)
service.start()

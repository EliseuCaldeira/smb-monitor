#import traceback
import logging
log = logging.getLogger('root')

import subprocess
import threading
import time
import signal
from http.server import ThreadingHTTPServer
from include.DB import DB
from datetime import datetime, timedelta, timezone
from include.Audit_File import Audit_File
from include.http import WebRequestHandler
from include.Email import Email

# The flowing makes the program handle Ctrl+C (SIGINT) gracefully:
exit_event = threading.Event()
def signal_handler(signum, frame):
	exit_event.set()
signal.signal(signal.SIGINT, signal_handler)

# Class Service:
class Service:
	def __init__(
		self,
		AUDITS,
		DELAY: int,
		HTTP_PORT: int,
		EMAIL_BOX: str,
		EMAIL_PASSWORD: str,
		SMTP: str,
		SMTP_PORT: int,
		EMAIL_RECIPIENT: str,
		ZABBIX_SERVER_IP: str | None,
		ZABBIX_SERVER_PORT: int,
		ZABBIX_THIS_HOST: str | None,
		EXCESSIVE_UNLINKS_THRESHOLD: int,
		EXCESSIVE_UNLINKS_TIME_WINDOW: int,
		EXCESSIVE_UNLINKS_COOLDOWN: int,
		EXCESSIVE_MOVES_THRESHOLD: int,
		EXCESSIVE_MOVES_TIME_WINDOW: int,
		EXCESSIVE_MOVES_COOLDOWN: int
	):
		self.audits = AUDITS
		self.delay = DELAY
		self.http_port = HTTP_PORT
		self.email_box = EMAIL_BOX
		self.email_password = EMAIL_PASSWORD
		self.smtp = SMTP
		self.smtp_port = SMTP_PORT
		self.email_recipient = EMAIL_RECIPIENT
		self.zabbix_server_ip = ZABBIX_SERVER_IP
		self.zabbix_server_port = ZABBIX_SERVER_PORT
		self.zabbix_this_host = ZABBIX_THIS_HOST
		self.excessive_unlinks_threshold = EXCESSIVE_UNLINKS_THRESHOLD
		self.excessive_unlinks_time_window = EXCESSIVE_UNLINKS_TIME_WINDOW
		self.excessive_unlinks_cooldown = EXCESSIVE_UNLINKS_COOLDOWN
		self.excessive_moves_threshold = EXCESSIVE_MOVES_THRESHOLD
		self.excessive_moves_time_window = EXCESSIVE_MOVES_TIME_WINDOW
		self.excessive_moves_cooldown = EXCESSIVE_MOVES_COOLDOWN
		# List of instances of Audit_File:
		self.audit_files: list[Audit_File] = []
		# A list that holds information about alerts sent recently on excessive unlinks
		# Each element is a dictionary with the following keys:
		# - user_id: int
		# - share_id: int
		# - utc_timestamp: int
		self.alerts_sent_on_excessive_unlinks = []
		# A list that holds information about alerts sent recently on excessive moves
		# Each element is a dictionary with the following keys:
		# - user_id: int
		# - share_id: int
		# - utc_timestamp: int
		self.alerts_sent_on_excessive_moves = []

	def start(self):
		# Start main thread:
		main_thread = threading.Thread(target=self.run, daemon=False)
		main_thread.start()
		log.debug("Main thread started")

		# HTTP server start:
		# ThreadingHTTPServer is used, so that every new connection to it, is a new thread
		http_server = ThreadingHTTPServer((r"", self.http_port), WebRequestHandler)
		http_server_thread = threading.Thread(target=http_server.serve_forever)
		http_server_thread.daemon = True
		http_server_thread.start()
		log.info(f"HTTP server is using port:{self.http_port}")

		# Stop main thread:
		while main_thread.is_alive():
			main_thread.join(timeout=0.5)
		log.debug("Main thread stopped")

	def __del__(self):
		log.warning("/!\\ Service was stopped /!\\")

	def run(self):
		# Open Database connection:
		db = DB()
		# Define what files to read:
		self.load_audit_files(db)
		# To avoid stressing the CPU, execute only one function per loop iteration.
		# Map functions to loop cycle count:
		function_per_loop = {
			1: self.read_audits,
			2: self.check_excessive_unlinks,
			3: self.read_audits,
			4: self.check_excessive_moves,
			5: self.read_audits,
			6: self.send_zabbix_reports
		}
		max_loop_count = max(function_per_loop.keys())
		# This variable is used to iterate between function_per_loop:
		loop_count = 0
		# The thread loop:
		while not exit_event.is_set():
			# Increment loop_counter:
			loop_count += 1
			# Delay:
			time.sleep(self.delay)
			# To execute every loop, put the respective function here:
			##execute_every_loop()
			# Execute only on loop n, according to function_per_loop dict:
			if loop_count in function_per_loop:
				function_per_loop[loop_count](db)
			# Reset loop_counter:
			if loop_count >= max_loop_count:
				loop_count = 0
		# Close DB connection:
		del db

	def load_audit_files(self, db):
		"""
		<h2>load_audit_files</h2>
		Initialize self.audit_files from configuration.
		"""
		log.debug("Loading audit files to memory...")
		# First, add new found audit files to the database:
		for key, value in self.audits.items():
			query_string = f"""--sql
INSERT INTO Audit_Files(file_path, line_number)
VALUES ("{value[0]}", 1)
ON CONFLICT(file_path) DO NOTHING;"""
			db.query(query_string)
		# Then, query database for all audit_files stored:
		query_string = """--sql
SELECT * FROM Audit_Files;"""
		result = db.query(query_string)
		# Temporary list of audit files:
		audit_files = []
		for row in result:
			cols = {}
			for col in row.keys():
				cols[col] = row[col]
			audit_files.append(cols)
		# Finally, append instances of audit files to be read to self.audit_files:
		log_string = r"Audit files added to memory:"
		# Files that are present on the database, but not on the config file, can stay on the DB unchanged, 
		# but are ignored for this run...
		count = 0
		for key, value in self.audits.items():
			for audit_file in audit_files:
				if value[0] == audit_file[r"file_path"]:
					if not audit_file[r"line_number"] or audit_file[r"line_number"] < 1:
						audit_file[r"line_number"] = 1
					if not audit_file[r"first_line"]:
						audit_file[r"first_line"] = r"new file"
					self.audit_files.append(
						Audit_File(
							file_path = value[0],
							line_number = audit_file[r"line_number"],
							first_line = audit_file[r"first_line"],
							path_prefix_to_ignore = value[1],
							timezone = value[2]
						)
					)
					log_string += (
						f"\n\naudit_file[{count}][\"file_path\"] = "
						f"\"{self.audit_files[count].file_path}\""
						f"\naudit_file[{count}][\"line_number\"] = "
						f"{self.audit_files[count].line_number}"
						f"\naudit_file[{count}][\"first_line\"] = "
						f"\"{self.audit_files[count].first_line}\""
						f"\naudit_file[{count}][\"path_prefix_to_ignore\"] = "
						f"\"{self.audit_files[count].path_prefix_to_ignore}\""
						f"\naudit_file[{count}][\"timezone\"] = "
						f"\"{self.audit_files[count].timezone}\""
					)
					count += 1
		log.info(log_string)
		# Restore cursor position for each file:
		for audit_file in self.audit_files:
			##log.debug(f"restore_cursor_position({audit_file.file_path})")
			self.restore_cursor_position(db, audit_file)

	def restore_cursor_position(self, db, audit_file: Audit_File):
		"""
		<h2>restore_cursor_position</h2>
		Restores the cursor to its last known position in the audit file.

		If the file has not been reset, the cursor is placed at the saved position.
		If the file has been reset, the cursor is moved to the start of the file.
		If there is a problem accessing the file, it exits without modifying the saved state.
		"""
		#log.debug("restore_cursor_position")
		# Try to open the file:
		try:
			with open(audit_file.file_path, 'r', encoding='utf-8') as cursor:
				pass
			##cursor = open(audit_file.file_path, 'r', encoding='utf-8')
			##audit_file.file_cursor = cursor
			audit_file.file_ok = True
		except:
			##log.warning(f"File \"{audit_file.file_path}\" could not be opened!")
			audit_file.file_ok = False
		# If the file was successfully opened:
		if audit_file.file_ok:
			line_number, first_line = audit_file.goto_line()
			if line_number == 0:
				audit_file.file_ok = False
				return
			if line_number < 1 or first_line is None:
				line_number = 1
				first_line = r"new file"
			# Update Audit_Files table in DB:
			query_string = f"""--sql
UPDATE Audit_Files SET
line_number = {line_number},
first_line = "{first_line}"
WHERE file_path = "{audit_file.file_path}";"""
			#log.debug(f"query_string:\n{query_string}")
			db.query(query_string)

	def read_audits(self, db):
		# For each audit_file:
		for audit_file in self.audit_files:
			
			if not audit_file.file_ok:
				#log.debug(f"Audit file \"{audit_file.file_path}\" is not Okay\nTrying to restore its cursor...")
				self.restore_cursor_position(db, audit_file)
			
			if not audit_file.file_ok:
				#log.debug(f"Audit file \"{audit_file.file_path}\"'s cursor could not be restored\nWe'll try later.")
				continue

			# Exhaust potential new lines:
			while audit_file.file_ok:
				continue_reading, event = audit_file.read_next()



				##log.debug(f"read audit_file -> {audit_file.file_path}\ncontinue_reading: {continue_reading}\nevent: {event}")


				# Put patters to ignore inside this condition
				if(
					event is not None
					and(
						not event.node1_list[-1][1].startswith("~")
						and not event.node1_list[-1][1].endswith((".tmp", ".$$$", ".crdownload"))
					)
					and(
						event.node2_list is None
						or(
							not event.node2_list[-1][1].startswith("~")
							and not event.node2_list[-1][1].endswith((".tmp", ".$$$", ".crdownload"))
						)
					)
				):
					# Process event:
					# 1st, store the user and retrieve its id
					db.query(f"""--sql
INSERT INTO Users(user_name, user_host, user_ip)
VALUES ("{event.user_name}", "{event.user_host}", "{event.user_ip}")
ON CONFLICT(user_name, user_host, user_ip) DO NOTHING;"""
					)
					user_id = db.query(f"""--sql
SELECT user_id FROM Users
WHERE user_name="{event.user_name}"
AND user_host="{event.user_host}"
AND user_ip="{event.user_ip}";"""
					)[0][r"user_id"]

					# 2nd, store the share and retrieve its id
					db.query(f"""--sql
INSERT INTO Shares(share_name, share_host, share_path)
VALUES ("{event.share_name}", "{event.share_host}", "{event.share_path}")
ON CONFLICT(share_name, share_host) DO NOTHING;"""
					)
					share_id = db.query(f"""--sql
SELECT share_id FROM Shares
WHERE share_name="{event.share_name}"
AND share_host="{event.share_host}";"""
					)[0][r"share_id"]

					# 3rd, store list of nodes and retrieve their id's:
					for path, name in event.node1_list:
						db.query(f"""--sql
INSERT INTO Nodes(node_path, share_id, node_name)
VALUES ("{path}", {share_id}, "{name}")
ON CONFLICT(node_path, share_id) DO NOTHING;"""
						)
					path, _ = event.node1_list[-1]
					#log.debug(f"path = \"{path}\", share_id = {share_id}")
					node1_id = db.query(f"""--sql
SELECT node_id FROM Nodes
WHERE node_path="{path}"
AND share_id={share_id};"""
					)[0][r"node_id"]
					# In case there is a second node:
					if event.node2_list is not None:
						for path, name in event.node2_list:
							db.query(f"""--sql
INSERT INTO Nodes(node_path, share_id, node_name)
VALUES ("{path}", {share_id}, "{name}")
ON CONFLICT(node_path, share_id) DO NOTHING;"""
							)
						path, _ = event.node2_list[-1]
						node2_id = db.query(f"""--sql
SELECT node_id FROM Nodes
WHERE node_path="{path}"
AND share_id={share_id};"""
						)[0][r"node_id"]
						# 4th, store event with 2 nodes:
						db.query(f"""--sql
INSERT INTO Events(user_id, share_id, node1_id, node2_id, utc_timestamp, event_type)
VALUES ({user_id}, {share_id}, {node1_id}, {node2_id}, {event.utc_timestamp}, {event.event_type});"""
						)
					else:
						# 4th, store event with single node:
						db.query(f"""--sql
INSERT INTO Events(user_id, share_id, node1_id, utc_timestamp, event_type)
VALUES ({user_id}, {share_id}, {node1_id}, {event.utc_timestamp}, {event.event_type});"""
						)
				
				# Stop reading new lines:
				elif not continue_reading:
					break
			
			# Update Audit_Files table:
			db.query(f"""--sql
UPDATE Audit_Files SET
line_number = {audit_file.line_number},
first_line = "{audit_file.first_line}"
WHERE file_path = "{audit_file.file_path}";"""
			)


	def check_excessive_unlinks(self, db):
		# Calculate time limit by subtracting EXCESSIVE_UNLINKS_TIME_WINDOW from current utc time:
		utc_now: int = int(datetime.now(timezone.utc).timestamp())
		time_limit: int = int((datetime.now(timezone.utc) - timedelta(seconds=self.excessive_unlinks_time_window)).timestamp())
		cooldown: int = int((datetime.now(timezone.utc) - timedelta(seconds=self.excessive_unlinks_cooldown)).timestamp())
		# First, clear all records from alerts_sent_on_excessive_unlinks that are older than cooldown:
		for alert in list(self.alerts_sent_on_excessive_unlinks):
			if alert["utc_timestamp"] < cooldown:
				self.alerts_sent_on_excessive_unlinks.remove(alert)
		# Gather info about all recent excessive unlinks:
		result = db.query(f"""--sql
SELECT
	Users.user_id,
	Users.user_name,
	Users.user_host,
	Users.user_ip,
	Shares.share_id,
	Shares.share_host,
	Shares.share_name,
	Nodes.node_path,
	Events.utc_timestamp,
	Events.event_type
FROM Events
INNER JOIN Users ON Events.user_id = Users.user_id
INNER JOIN Shares ON Events.share_id = Shares.share_id
INNER JOIN Nodes ON Events.node1_id = Nodes.node_id
WHERE Events.event_type = 0
AND Events.utc_timestamp > {time_limit};"""
		)
		excessive_unlinks = []
		for row in result:
			cols = {}
			for col in row.keys():
				cols[col] = row[col]
			excessive_unlinks.append(cols)
		# Count the occurence of the combination of user_id and share_id:
		user_share_count = {}
		for excessive_unlink in excessive_unlinks:
			key = (excessive_unlink["user_id"], excessive_unlink["share_id"])
			if key not in user_share_count:
				user_share_count[key] = 1
			else:
				user_share_count[key] += 1
		# Build fast lookup of recent alerts:
		recent_alerts = {
			(alert["user_id"], alert["share_id"])
			for alert in self.alerts_sent_on_excessive_unlinks
		}
		# Map each (user_id, share_id) to a list of node_paths:
		nodes_per_user_share = {}
		for excessive_unlink in excessive_unlinks:
			key = (excessive_unlink["user_id"], excessive_unlink["share_id"])
			if key not in nodes_per_user_share:
				nodes_per_user_share[key] = []
			nodes_per_user_share[key].append(excessive_unlink["node_path"])
		# Pick a representative row for each (user_id, share_id):
		representative_rows = {}
		for excessive_unlink in excessive_unlinks:
			key = (excessive_unlink["user_id"], excessive_unlink["share_id"])
			if key not in representative_rows:
				representative_rows[key] = excessive_unlink
		# Iterate through user_share_count and check threshold:
		for (user_id, share_id), count in user_share_count.items():
			if count >= self.excessive_unlinks_threshold:
				if (user_id, share_id) not in recent_alerts:
					# Trigger alert
					email = Email(
						email_box=self.email_box,
						email_password=self.email_password,
						smtp=self.smtp,
						smtp_port=self.smtp_port,
						email_recipient=self.email_recipient,
						email_type="unlink",
						user_name=representative_rows[(user_id, share_id)]["user_name"],
						user_host=representative_rows[(user_id, share_id)]["user_host"],
						user_ip=representative_rows[(user_id, share_id)]["user_ip"],
						share_host=representative_rows[(user_id, share_id)]["share_host"],
						share_name=representative_rows[(user_id, share_id)]["share_name"],
						node1_path_list=nodes_per_user_share[(user_id, share_id)],
						node2_path_list=None
					)
					email.send_email()
					# Add to recent_alerts
					self.alerts_sent_on_excessive_unlinks.append(
						{
							"user_id": user_id,
							"share_id": share_id,
							"utc_timestamp": utc_now
						}
					)


	def check_excessive_moves(self, db):
		# Calculate time limit by subtracting EXCESSIVE_MOVES_TIME_WINDOW from current utc time:
		utc_now: int = int(datetime.now(timezone.utc).timestamp())
		time_limit: int = int((datetime.now(timezone.utc) - timedelta(seconds=self.excessive_moves_time_window)).timestamp())
		cooldown: int = int((datetime.now(timezone.utc) - timedelta(seconds=self.excessive_moves_cooldown)).timestamp())
		# First, clear all records from alerts_sent_on_excessive_moves that are older than cooldown:
		for alert in list(self.alerts_sent_on_excessive_moves):
			if alert["utc_timestamp"] < cooldown:
				self.alerts_sent_on_excessive_moves.remove(alert)
		# Gather info about all recent excessive moves:
		result = db.query(f"""--sql
SELECT
	Users.user_id,
	Users.user_name,
	Users.user_host,
	Users.user_ip,
	Shares.share_id,
	Shares.share_host,
	Shares.share_name,
	Events.utc_timestamp,
	Events.event_type,
	Nodes1.node_path node1_path,
	Nodes1.node_name node1_name,
	Nodes2.node_path node2_path,
	Nodes2.node_name node2_name
FROM Events
INNER JOIN Users ON Events.user_id = Users.user_id
INNER JOIN Shares ON Events.share_id = Shares.share_id
INNER JOIN Nodes Nodes1 ON Events.node1_id = Nodes1.node_id
LEFT OUTER JOIN Nodes Nodes2 ON Events.node2_id = Nodes2.node_id
WHERE Events.event_type = 2
AND Nodes1.node_name = Nodes2.node_name
AND Events.utc_timestamp > {time_limit};"""
		)
		excessive_moves = []
		for row in result:
			cols = {}
			for col in row.keys():
				cols[col] = row[col]
			excessive_moves.append(cols)
		# Count the occurence of the combination of user_id and share_id:
		user_share_count = {}
		for excessive_move in excessive_moves:
			key = (excessive_move["user_id"], excessive_move["share_id"])
			if key not in user_share_count:
				user_share_count[key] = 1
			else:
				user_share_count[key] += 1
		# Build fast lookup of recent alerts:
		recent_alerts = {
			(alert["user_id"], alert["share_id"])
			for alert in self.alerts_sent_on_excessive_moves
		}
		# Map each (user_id, share_id) to a list of node1_paths:
		nodes1_per_user_share = {}
		for excessive_move in excessive_moves:
			key = (excessive_move["user_id"], excessive_move["share_id"])
			if key not in nodes1_per_user_share:
				nodes1_per_user_share[key] = []
			nodes1_per_user_share[key].append(excessive_move["node1_path"])
		# Map each (user_id, share_id) to a list of node2_paths:
		nodes2_per_user_share = {}
		for excessive_move in excessive_moves:
			key = (excessive_move["user_id"], excessive_move["share_id"])
			if key not in nodes2_per_user_share:
				nodes2_per_user_share[key] = []
			nodes2_per_user_share[key].append(excessive_move["node2_path"])
		# Pick a representative row for each (user_id, share_id):
		representative_rows = {}
		for excessive_move in excessive_moves:
			key = (excessive_move["user_id"], excessive_move["share_id"])
			if key not in representative_rows:
				representative_rows[key] = excessive_move
		# Iterate through user_share_count and check threshold:
		for (user_id, share_id), count in user_share_count.items():
			if count >= self.excessive_moves_threshold:
				if (user_id, share_id) not in recent_alerts:
					# Trigger alert
					email = Email(
						email_box=self.email_box,
						email_password=self.email_password,
						smtp=self.smtp,
						smtp_port=self.smtp_port,
						email_recipient=self.email_recipient,
						email_type="move",
						user_name=representative_rows[(user_id, share_id)]["user_name"],
						user_host=representative_rows[(user_id, share_id)]["user_host"],
						user_ip=representative_rows[(user_id, share_id)]["user_ip"],
						share_host=representative_rows[(user_id, share_id)]["share_host"],
						share_name=representative_rows[(user_id, share_id)]["share_name"],
						node1_path_list=nodes1_per_user_share[(user_id, share_id)],
						node2_path_list=nodes2_per_user_share[(user_id, share_id)]
					)
					email.send_email()
					# Add to recent_alerts
					self.alerts_sent_on_excessive_moves.append(
						{
							"user_id": user_id,
							"share_id": share_id,
							"utc_timestamp": utc_now
						}
					)

	def send_zabbix_reports(self, db):
		#log.debug("Sending Zabbix reports...")
		if self.zabbix_server_ip is None:
			# Zabbix server IP is not configured
			return

		time_limit: int = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())

		zabbix_keys: list[str] = [
			"smb-monitor.unlinks-per-minute",
			"smb-monitor.moves-per-minute",
			"smb-monitor.renames-per-minute",
			"smb-monitor.mkdirs-per-minute"
		]

		# Give general report:
		if self.zabbix_this_host is not None:
			# unlik count:
			unlinks = db.query(f"""--sql
SELECT count(*) AS total
FROM Events
WHERE Events.event_type = 0
AND Events.utc_timestamp > {time_limit};""")[0][r"total"]
			# Send general unlik count report to zabbix:
			try:
				result = subprocess.run(
					[
						"zabbix_sender",
						"-z", str(self.zabbix_server_ip),
						"-p", str(self.zabbix_server_port),
						"-s", str(self.zabbix_this_host),
						"-k", str(zabbix_keys[0]),
						"-o", str(unlinks)
					],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text = True
				)
				#log.debug(f"stdout\n{result.stdout}\n\nstderr\n{result.stderr}")
			except Exception as e:
				log.error(f"Error sending Zabbix report: {e}")
			# move count:
			moves = db.query(f"""--sql
SELECT count(*) AS total
FROM Events
INNER JOIN Nodes Nodes1 ON Events.node1_id = Nodes1.node_id
LEFT OUTER JOIN Nodes Nodes2 ON Events.node2_id = Nodes2.node_id
WHERE Events.event_type = 2
AND Nodes1.node_name = Nodes2.node_name
AND Events.utc_timestamp > {time_limit};""")[0][r"total"]
			# Send general move count report to zabbix:
			try:
				result = subprocess.run(
					[
						"zabbix_sender",
						"-z", str(self.zabbix_server_ip),
						"-p", str(self.zabbix_server_port),
						"-s", str(self.zabbix_this_host),
						"-k", str(zabbix_keys[1]),
						"-o", str(moves)
					],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text = True
				)
				#log.debug(f"stdout\n{result.stdout}\n\nstderr\n{result.stderr}")
			except Exception as e:
				log.error(f"Error sending Zabbix report: {e}")
			# rename count:
			renames = db.query(f"""--sql
SELECT count(*) AS total
FROM Events
INNER JOIN Nodes Nodes1 ON Events.node1_id = Nodes1.node_id
LEFT OUTER JOIN Nodes Nodes2 ON Events.node2_id = Nodes2.node_id
WHERE Events.event_type = 2
AND Nodes1.node_name != Nodes2.node_name
AND Events.utc_timestamp > {time_limit};""")[0][r"total"]
			# Send general rename count report to zabbix:
			try:
				result = subprocess.run(
					[
						"zabbix_sender",
						"-z", str(self.zabbix_server_ip),
						"-p", str(self.zabbix_server_port),
						"-s", str(self.zabbix_this_host),
						"-k", str(zabbix_keys[2]),
						"-o", str(renames)
					],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text = True
				)
				#log.debug(f"stdout\n{result.stdout}\n\nstderr\n{result.stderr}")
			except Exception as e:
				log.error(f"Error sending Zabbix report: {e}")
			# mkdir count:
			mkdirs = db.query(f"""--sql
SELECT count(*) AS total
FROM Events
WHERE Events.event_type = 1
AND Events.utc_timestamp > {time_limit};""")[0][r"total"]
			# Send general mkdir count report to zabbix:
			try:
				result = subprocess.run(
					[
						"zabbix_sender",
						"-z", str(self.zabbix_server_ip),
						"-p", str(self.zabbix_server_port),
						"-s", str(self.zabbix_this_host),
						"-k", str(zabbix_keys[3]),
						"-o", str(mkdirs)
					],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text = True
				)
				#log.debug(f"stdout\n{result.stdout}\n\nstderr\n{result.stderr}")
			except Exception as e:
				log.error(f"Error sending Zabbix report: {e}")
		
		# Send per Share.host report:
		hosts = db.query("""--sql
SELECT DISTINCT share_host
FROM Shares;""")
		share_host_rows = []
		for host in hosts:
			cols = {}
			for col in host.keys():
				cols[col] = host[col]
			share_host_rows.append(cols)
		for host in share_host_rows:
			host = host["share_host"]
			# unlik count:
			unlinks = db.query(f"""--sql
SELECT count(*) AS total
FROM Events
INNER JOIN Shares ON Events.share_id = Shares.share_id
WHERE Events.event_type = 0
AND Shares.share_host = "{host}"
AND Events.utc_timestamp > {time_limit};""")[0][r"total"]
			# Send per Share.host unlik count report to zabbix:
			try:
				result = subprocess.run(
					[
						"zabbix_sender",
						"-z", str(self.zabbix_server_ip),
						"-p", str(self.zabbix_server_port),
						"-s", f"Server - {host.upper()}",
						"-k", str(zabbix_keys[0]),
						"-o", str(unlinks)
					],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text = True
				)
			except Exception as e:
				log.error(f"Error sending Zabbix report: {e}")
			moves = db.query(f"""--sql
SELECT count(*) AS total
FROM Events
INNER JOIN Shares ON Events.share_id = Shares.share_id
INNER JOIN Nodes Nodes1 ON Events.node1_id = Nodes1.node_id
LEFT OUTER JOIN Nodes Nodes2 ON Events.node2_id = Nodes2.node_id
WHERE Events.event_type = 2
AND Shares.share_host = "{host}"
AND Nodes1.node_name = Nodes2.node_name
AND Events.utc_timestamp > {time_limit};""")[0][r"total"]
			# Send per Share.host move count report to zabbix:
			try:
				result = subprocess.run(
					[
						"zabbix_sender",
						"-z", str(self.zabbix_server_ip),
						"-p", str(self.zabbix_server_port),
						"-s", f"Server - {host.upper()}",
						"-k", str(zabbix_keys[1]),
						"-o", str(moves)
					],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text = True
				)
			except Exception as e:
				log.error(f"Error sending Zabbix report: {e}")
			# rename count:
			renames = db.query(f"""--sql
SELECT count(*) AS total
FROM Events
INNER JOIN Shares ON Events.share_id = Shares.share_id
INNER JOIN Nodes Nodes1 ON Events.node1_id = Nodes1.node_id
LEFT OUTER JOIN Nodes Nodes2 ON Events.node2_id = Nodes2.node_id
WHERE Events.event_type = 2
AND Shares.share_host = "{host}"
AND Nodes1.node_name != Nodes2.node_name
AND Events.utc_timestamp > {time_limit};""")[0][r"total"]
			# Send per Share.host rename count report to zabbix:
			try:
				result = subprocess.run(
					[
						"zabbix_sender",
						"-z", str(self.zabbix_server_ip),
						"-p", str(self.zabbix_server_port),
						"-s", f"Server - {host.upper()}",
						"-k", str(zabbix_keys[2]),
						"-o", str(renames)
					],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text = True
				)
			except Exception as e:
				log.error(f"Error sending Zabbix report: {e}")
			# mkdir count:
			mkdirs = db.query(f"""--sql
SELECT count(*) AS total
FROM Events
INNER JOIN Shares ON Events.share_id = Shares.share_id
WHERE Events.event_type = 1
AND Shares.share_host = "{host}"
AND Events.utc_timestamp > {time_limit};""")[0][r"total"]
			# Send per Share.host mkdir count report to zabbix:
			try:
				result = subprocess.run(
					[
						"zabbix_sender",
						"-z", str(self.zabbix_server_ip),
						"-p", str(self.zabbix_server_port),
						"-s", f"Server - {host.upper()}",
						"-k", str(zabbix_keys[3]),
						"-o", str(mkdirs)
					],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text = True
				)
			except Exception as e:
				log.error(f"Error sending Zabbix report: {e}")

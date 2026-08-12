#import traceback
import logging
log = logging.getLogger('root')

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


class Event:

	def __init__(self, raw_event: str, timezone_name: str, path_prefix_to_ignore: str):
		#log.debug(f"New Event {raw_event}, {timezone_name}, {path_prefix_to_ignore}")
		# Timezone:
		self.timezone_name: str = timezone_name
		# Split the event at every | :
		event: list[str] = raw_event.split('|')
		# extract just the date and time from the first part of the raw_audit:
		date_time: str = " ".join(event[0].split()[:3])
		# Events.timestamp:
		self.utc_timestamp: int | None = self.interpret_timestamp(date_time)
		#log.debug(f"self.utc_timestamp -> {self.utc_timestamp}")
		# Shares.share_hostname
		self.share_host: str = event[0].split()[3]
		# Actors.actor_username:
		self.user_name: str = event[0].split()[-1]
		# Actors.actor_hostname:
		self.user_host: str = event[2]
		# Actors.actor_ip:
		self.user_ip: str = event[1]
		# Shares.share_name:
		self.share_name: str = event[3]
		# Events.event_type:
		possible_events: dict[str, int] = {r"unlinkat": 0, r"mkdirat": 1, r"renameat": 2}
		# defaults to 0
		self.event_type: int = possible_events.get(event[4], 0)

		## List of all parent nodes of node_1
		##self.node1_list: list[str]
		## List of all parent nodes of node_2
		##self.node2_list: list[str] | None

		# Nodes.node_path (1):
		self.node1_path: str = event[6]
		if self.node1_path.startswith(path_prefix_to_ignore):
			self.node1_path = self.node1_path[len(path_prefix_to_ignore):]
		node1_parts: list[str] = self.node1_path.split('/')
		# Shares.share_path (1):
		self.share_path: str = node1_parts[0]
		# Nodes.node_name (1):
		self.node1_name = node1_parts[-1]
		# Nodes.node_path (2):
		self.node2_path: str | None = None
		# Nodes.node_name (2):
		self.node2_name: str | None = None

		# List of all parent nodes of node_1:
		self.node1_list: list[tuple[str, str]] = [
			(r"/".join(node1_parts[:i + 1]), node1_parts[i])
			for i in range(len(node1_parts))
		]

		# List of all parent nodes of node_2:
		self.node2_list: list[tuple[str, str]] | None = None
		if self.event_type == 2 and len(event) > 7:
			self.node2_path = event[7]
			if self.node2_path.startswith(path_prefix_to_ignore):
				self.node2_path = self.node2_path[len(path_prefix_to_ignore):]
			node2_parts: list[str] = self.node2_path.split('/')
			# Nodes.node_name (2)
			self.node2_name = node2_parts[-1]
			# List of all parent nodes of node_2
			self.node2_list = [
				(r"/".join(node2_parts[:i + 1]), node2_parts[i])
				for i in range(len(node2_parts))
			]
		#log.debug(f"Event created")
		


	def interpret_timestamp(self, date_time: str) -> int | None:
		#log.debug(f"interpret_timestamp {date_time}")
		# fix double first letter
		if len(date_time) > 1 and date_time[0] == date_time[1]:
			date_time = date_time[1:]

		# Current local time (self.timezone)
		#log.debug(f"Before ZoneInfo({self.timezone_name})")
		local_now: datetime = datetime.now(tz = ZoneInfo(self.timezone_name))
		#IF THE FOLLOWING DOESN'T LOG, pip install tzdata
		#log.debug("After ZoneInfo()")
		current_local_year: int = local_now.year
		event_date_time_format: str = r"%b %d %H:%M:%S"

		try:
			event_date_time: datetime = datetime.strptime(
				date_time, event_date_time_format
			).replace(
				year=current_local_year, tzinfo = ZoneInfo(self.timezone_name)
			)
		except ValueError:
			return None
		
		# Test if event is in the future:
		if event_date_time > local_now + timedelta(hours = 25):
			# If so, replace year with previous one:
			event_date_time = event_date_time.replace(year = current_local_year - 1)

		return int(event_date_time.astimezone(timezone.utc).timestamp())

#import traceback
import logging
log = logging.getLogger('root')

import json
from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qsl, urlparse
from include.DB import DB
from datetime import datetime, timedelta, timezone
import re

class WebRequestHandler(BaseHTTPRequestHandler):

	# The following dictionary, contains the only valid files that this small http server can serve.
	# The value attributed to each file (key), is the file's MIME type
	# Here's a list of common MIME types:
	# "text"       : "text/plain; charset=utf-8"
	# "json"       : "application/json; charset=utf-8"
	# "html"       : "text/html; charset=utf-8"
	# "css"        : "text/css; charset=utf-8"
	# "javascript" : "text/javascript; charset=utf-8"
	# "favicon.ico": "image/x-icon"
	valid_file_type = {
		r"favicon.ico"      : r"image/x-icon",
		r"default.css"      : r"text/css; charset=utf-8",
		r"bootstrap.css"    : r"text/css; charset=utf-8",
		r"bootstrap.css.map": r"application/json; charset=utf-8",
		r"bootstrap.js"     : r"text/javascript; charset=utf-8",
		r"bootstrap.js.map" : r"application/json; charset=utf-8",
		r"main.js"          : r"text/javascript; charset=utf-8",
		r"jquery.js"        : r"text/javascript; charset=utf-8",
		r"index.html"       : r"text/html; charset=utf-8"
	}

	@cached_property
	def url(self):
		return urlparse(self.path)

	@cached_property
	def query_data(self):
		return dict(parse_qsl(self.url.query))

	@cached_property
	def post_data(self):
		content_length = int(self.headers.get(r"Content-Length", 0))
		return self.rfile.read(content_length)

	@cached_property
	def form_data(self):
		return dict(parse_qsl(self.post_data.decode(r"utf-8")))

	@cached_property
	def cookies(self):
		return SimpleCookie(self.headers.get(r"Cookie"))

	# In case it receives a GET request:
	def do_GET(self):

		content = ""
		
		url = self.url.path.lstrip('/')

		#app_log.debug(f"   url: '{url}'")
		if url not in self.valid_file_type:
			url = r"index.html"
			#app_log.debug(f"-> url: '{url}'")

		# Send response status code
		self.send_response(200, r"OK")

		# Open file
		if url == r"favicon.ico":
			with open(r"./include/HTTP/favicon.ico", r"rb") as file:
				content = file.read()
				message = content
		else:
			with open(f"./include/HTTP/{url}", r"r", encoding=r"utf-8") as file:
				content = file.read()
				message = bytes(content, r"utf8")

		# Send headers
		self.send_header(r"Content-type", self.valid_file_type[url])
		self.send_header(r"Content-length", str(len(message)))
		self.end_headers()

		# Write content as utf-8 data
		self.wfile.write(message)
		return

	# In case it receives a POST request:
	def do_POST(self):
		# Open connection to the database:
		db: DB = DB()
		# Decode the received data as a utf-8 string:
		post_data: str	= self.post_data.decode(r"utf-8")
		# Interpret the received data as json:
		json_message	= json.loads(post_data)
		# Extract variables from json:
		share_host	= json_message.get(r"share_host")
		share_name	= json_message.get(r"share_name")
		time_span	= json_message.get(r"time_span")
		user_search	= json_message.get(r"user_search")
		time_order	= json_message.get(r"time_order")
		node_search	= json_message.get(r"node_search")
		# Initialize the query string:
		query_string: str = r"""
SELECT
utc_timestamp, event_type, user_name, user_host, user_ip, share_name, share_host,
Nodes1.node_path node1_path, Nodes1.node_name node1_name, Nodes2.node_path node2_path, Nodes2.node_name node2_name
FROM Events
INNER JOIN Users ON Events.user_id = Users.user_id
INNER JOIN Shares ON Events.share_id = Shares.share_id
INNER JOIN Nodes Nodes1 ON Events.node1_id = Nodes1.node_id
LEFT OUTER JOIN Nodes Nodes2 ON Events.node2_id = Nodes2.node_id
"""
		# To know if it's the first condition. If False, it is prefixed with an "AND ":
		first_filter = True
		# Initialize the content of the response:
		json_content: str = r""
		# Transform time_span into an integer:
		time_limit: int = 0
		datetime_limit: datetime | None = None
		if time_span == r"10m":
			datetime_limit = datetime.now(timezone.utc) - timedelta(minutes = 10)
		elif time_span == r"1h":
			datetime_limit = datetime.now(timezone.utc) - timedelta(hours = 1)
		elif time_span == r"1d":
			datetime_limit = datetime.now(timezone.utc) - timedelta(days = 1)
		elif time_span == r"1w":
			datetime_limit = datetime.now(timezone.utc) - timedelta(weeks = 1)
		elif time_span == r"1M":
			datetime_limit = datetime.now(timezone.utc) - timedelta(days = 31)# Shows more than a month, most times. But it's OK.
		if datetime_limit is not None:
			time_limit = int(datetime_limit.timestamp())
		# time_limit
		if time_limit > 0:
			query_string += f"WHERE Events.utc_timestamp > {time_limit}\n"
			first_filter = False
		# Interpret user_search:
		user_name, user_host, user_ip = self.parse_user_search(user_search)
		# user_name
		if user_name is not None:
			if not first_filter:
				query_string += r"AND "
			else:
				query_string += r"WHERE "
			query_string += f"Users.user_name LIKE \"{user_name}\"\n"
			first_filter = False
		# user_host
		if user_host is not None:
			if not first_filter:
				query_string += r"AND "
			else:
				query_string += r"WHERE "
			query_string += f"Users.user_host LIKE \"{user_host}\"\n"
			first_filter = False
		# user_ip
		if user_ip is not None:
			if not first_filter:
				query_string += r"AND "
			else:
				query_string += r"WHERE "
			query_string += f"Users.user_ip LIKE \"{user_ip}\"\n"
			first_filter = False
		# share_host
		if share_host is not None and len(share_host) > 0:
			if not first_filter:
				query_string += r"AND "
			else:
				query_string += r"WHERE "
			query_string += f"Shares.share_host = \"{share_host}\"\n"
			first_filter = False
		# share_name
		if share_name is not None and len(share_name) > 0:
			if not first_filter:
				query_string += r"AND "
			else:
				query_string += r"WHERE "
			query_string += f"Shares.share_name = \"{share_name}\"\n"
			first_filter = False
		# Parse node_search:
		node_path: str | None = None
		node_name: str | None = None
		if node_search is not None and len(node_search) > 0:
			node_search = node_search.replace("\\", "/")
			if node_search != r"/":
				if "/" in node_search:
					node_path = f"%{node_search}%"
				else:
					node_name = f"%{node_search}%"
		# node_path
		if node_path is not None:
			if not first_filter:
				query_string += r"AND "
			else:
				query_string += r"WHERE "
			query_string += f"(Nodes1.node_path LIKE \"{node_path}\" OR Nodes2.node_path LIKE \"{node_path}\")\n"
			first_filter = False
		# node_name
		if node_name is not None:
			if not first_filter:
				query_string += r"AND "
			else:
				query_string += r"WHERE "
			query_string += f"(Nodes1.node_name LIKE \"{node_name}\" OR Nodes2.node_name LIKE \"{node_name}\")\n"
			first_filter = False
		# time_order
		if time_order is not None and len(time_order) > 0:
			# ASC or DESC (ASC is the SQLite default behavior; DESC is this App's default behavior)
			if time_order == "ASC":
				query_string += f"ORDER BY Events.utc_timestamp ASC\n"
			else:
				query_string += f"ORDER BY Events.utc_timestamp DESC\n"
		else:
			query_string += f"ORDER BY Events.utc_timestamp DESC\n"
		# LIMIT
		query_string += r"LIMIT 1000;"
		# Query DB:
		##log.debug(f"query_string:\n{query_string}")
		result = db.query(query_string)
		# Process result:
		event_rows = []
		for row in result:
			cols = {}
			for col in row.keys():
				cols[col] = row[col]
			event_rows.append(cols)
		# List Servers
		query_string = r"""
SELECT DISTINCT share_host
FROM Shares;"""
		result = db.query(query_string)
		share_host_rows = []
		for row in result:
			cols = {}
			for col in row.keys():
				cols[col] = row[col]
			share_host_rows.append(cols)
		# List Shares, based on share_host
		share_name_rows = []
		if share_host is not None and len(share_host) > 0:
			query_string = f"""--sql
SELECT share_id, share_name FROM Shares
WHERE share_host = "{share_host}";"""
			result = db.query(query_string)
			share_name_rows = []
			for row in result:
				cols = {}
				for col in row.keys():
					cols[col] = row[col]
				share_name_rows.append(cols)
		# 
		content = {
			"events": event_rows,
			"servers": share_host_rows,
			"shares": share_name_rows
		}

		# 
		json_content = json.dumps(content)
		message = bytes(json_content, 'utf8')
		# Send response status code
		self.send_response(200, 'OK')
		# Send headers
		self.send_header('Content-type', "application/json; charset=utf-8")
		self.send_header('Content-length', str(len(message)))
		self.end_headers()
		# Write content as utf-8 data
		self.wfile.write(message)
		return



	# No futuro, executar isto no javascript...
	def parse_user_search(self, user_search):
		if not user_search:   # None or empty string
			return None, None, None

		s = user_search.strip()

		user_name = None
		user_host = None
		user_ip = None

		# ----- Extract IP -----
		# Case 1: "(" → everything to the right, stripped, gets "% at the end"
		if "(" in s:
			right = s.split("(", 1)[1]
			user_ip = right.strip()
			if user_ip:
				user_ip = user_ip + "%"
		else:
			# Case 2: ")" → take the token immediately left of ")"
			if ")" in s:
				left = s.split(")", 1)[0]
				# take the last token before ")"
				token = left.split()[-1]
				if token:
					user_ip = "%" + token

		# Remove everything including and after "(" or ")"
		s = re.split(r"[()]", s)[0].strip()

		# ----- Extract host and name -----
		if "@" in s:
			left, right = s.split("@", 1)

			# right → host
			host = right.replace(" ", "")
			if host:
				user_host = host + "%"

			# left → name
			name = left.replace(" ", "")
			if name:
				user_name = name + "%"
		else:
			# no "@": entire string is a name (no spaces)
			name = s.replace(" ", "")
			if name:
				user_name = name + "%"

		return user_name, user_host, user_ip


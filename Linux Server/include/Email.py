import traceback
import logging
log = logging.getLogger('root')

import smtplib, ssl
from email.message import EmailMessage


class Email:

	def __init__(
		self,
		email_box: str,
		email_password: str,
		smtp: str,
		smtp_port: int,
		email_recipient: str,
		email_type: str,
		user_name: str,
		user_host: str,
		user_ip: str,
		share_host: str,
		share_name: str,
		node1_path_list: list[str],
		node2_path_list: list[str] | None
	):
		self.email_box = email_box
		self.email_password = email_password
		self.smtp = smtp
		self.smtp_port = smtp_port
		self.email_recipient = email_recipient

		# Validate email_type:
		if email_type not in [r"unlink", r"move"]:
			log.warning(f"Invalid email_type: {email_type}")
			self.email_type: str = r"default"
		else:
			self.email_type: str = email_type
		
		self.user_name: str = user_name
		self.user_host: str = user_host
		self.user_ip: str = user_ip
		self.share_host: str = share_host
		self.share_name: str = share_name
		self.node1_path_list: list[str] = node1_path_list
		self.node2_path_list: list[str] | None = node2_path_list

	def send_email(self):
		email_subject: str = r"SMB: "
		email_body: str = r""
		if self.email_type == r"unlink":
			email_subject += r"Excess of Unlinks"
			nodes_html = "".join([f"<li>{node}</li>" for node in self.node1_path_list])
			email_body += f"""
<!DOCTYPE html>
<html>
<body>
	<h2>Excess of Unlinks detected</h2>
	<p><b>User:</b> 👨🏼‍💻{self.user_name}@{self.user_host}({self.user_ip})</p>
	<p><b>Share:</b> ☁️{self.share_host} 💿{self.share_name}</p>
	<p><b>Nodes deleted ({len(self.node1_path_list)}):</b></p>
	<ul>
		{nodes_html}
	</ul>
</body>
</html>
"""
		elif self.email_type == r"move":
			email_subject += r"Excess of Moves"
			nodes1_html = "".join([f"<li>{node}</li>" for node in self.node1_path_list])
			nodes2_html = "".join([f"<li>{node}</li>" for node in self.node2_path_list])
			email_body += f"""
<!DOCTYPE html>
<html>
<body>
	<h2>Excess of Moves detected</h2>
	<p><b>User:</b> 👨🏼‍💻{self.user_name}@{self.user_host}({self.user_ip})</p>
	<p><b>Share:</b> ☁️{self.share_host} 💿{self.share_name}</p>
	<p><b>Nodes deleted ({len(self.node1_path_list)}):</b></p>
	<ul>
		{nodes1_html}
	</ul>
	<p><b>Nodes moved to ({len(self.node2_path_list)}):</b></p>
	<ul>
		{nodes2_html}
	</ul>
</body>
</html>
"""
		else:
			email_subject += r"Invalid email type"
			email_body += f"""
<!DOCTYPE html>
<html>
<body>
	<h2>Invalid email type</h2>
	<p><b>Email type:</b> {self.email_type}</p>
</body>
</html>
"""
		# Create message:
		message = EmailMessage()
		message.set_content(email_body, subtype='html')
		message["Subject"] = email_subject
		message["From"] = self.email_box
		message["To"] = self.email_recipient
		# Send email:
		smtp = smtplib.SMTP(self.smtp, self.smtp_port)
		smtp.ehlo() # Send the extended hello to the server
		smtp.starttls() # Tell server we want to communicate with TLS encryption
		smtp.login(self.email_box, self.email_password) # Login to the server
		smtp.send_message(message) # Send the email
		smtp.quit() # Close the connection


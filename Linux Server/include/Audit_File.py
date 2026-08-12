import traceback
import logging
log = logging.getLogger('root')

from typing import TextIO
import io
from include.Event import Event

class Audit_File:
	"""
	<h1>Class: Audit_File</h1>
	Each instance holds information about an audit file to be interpreted.
	
	Attributes:
		file_path (str): Full path including filename.
		line_number (int): Next line to be read (starts at 1).
		first_line (str): First line of the file, used to detect resets.
		path_prefix_to_ignore (str): Portion of path to omit when processing.
		file_cursor (TextIO | None): Cursor for reading the file.
		byte_offset (int): Stores what byte the cursor is currently at.
	"""
	def __init__(
			self,
			file_path: str,
			line_number: int,
			first_line: str,
			path_prefix_to_ignore: str,
			timezone: str
	):
		self.file_path = file_path
		"""
		The file path, including filename, to the audit file to be read.
		"""
		
		self.line_number = 1
		"""
		The line it is currently ready to read. The file line number begins at 1 and not 0.
		"""

		self.first_line = r"new file"
		"""
		Contains the first line of the file. It is used to detect if file has been reset.
		"""

		if line_number > 1:
			self.line_number = line_number
			self.first_line = first_line

		self.path_prefix_to_ignore = path_prefix_to_ignore
		"""
		The first part of the node path to ignore.<br>
		Ex.:<br>
		self.path_prefix_to_ignore = "D:/Shared_Folder/"<br>
		And a node has full path: "D:/Shared_Folder/Specific_Share/Some_Folder/file.txt"<br>
		Only "Specific_Share/Some_Folder/file.txt" will be processed.
		"""

		self.timezone: str = timezone

		# The following is a BAD idea!
		##self.file_cursor: TextIO | None = None
		"""
		The cursor inside the audit file.
		"""

		self.byte_offset: int = 0
		"""
		Stores what byte the cursor currently is at.<br>
		It is the result of self.file_cursor.tell()
		"""

		self.file_ok = False
		"""
		Stores wether the audit file is present and readable (True), or is absent or unreadable (False).
		"""

		'''
		self.db: None | DB = None
		"""
		Each instance of this class, has a connection to the database.
		"""
		self.restore_cursor_position()
		'''

	def __del__(self):
		"""
		Safely close the connection to the Data Base and file cursor.
		"""
		...

	def goto_line(self, target_line_number: int | None = None) -> tuple[int, str]:
		"""
		<h2>goto_line</h2>
		Moves the file cursor to the beginning of line_number.

		Args:
			line_number (int | None): Line number to move to.
			If None, uses self.line_number

		Returns:
			tuple[int, str]: A tuple containing:
			The resulting status code:
				0: failure;
				-1: EOF reached before the target line;
				== line_number (or > 0): success.
			And the content of the first line of the file.

		Side Effects:
			Updates self.line_number, self.first_line, and self.byte_offset
		"""

		# Open the file:
		try:
			cursor = open(self.file_path, 'r', encoding='utf-8')
		except:
			log.warning(f"Something unforeseen happened, when trying goto_line({target_line_number})")
			self.file_ok = False
			if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
				cursor.close()
			return (0, "")

		if target_line_number is None:
			target_line_number = self.line_number

		# Try to reach the line:
		try:
			# Put the cursor at the beginning of the file:
			current_first_line = r"new file"
			current_byte_offset = 0
			cursor.seek(current_byte_offset)
			current_line_number = 1

			# If goto line 1 (or other value below):
			if target_line_number <= 1:
				# Log:
				log.info(f"File \"{self.file_path}\" is a new file.\nIts cursor will be positioned at byte offset: 0, line number: 1")
				# Update self.line_number, self.first_line and self.byte_offset:
				self.line_number = 1
				self.first_line = r"new file"
				self.byte_offset = 0
				# Return:
				if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
					cursor.close()
				return (1, r"new file")

			# Read first line:
			current_first_line = cursor.readline().strip()
			current_byte_offset = cursor.tell()
			# If line is not compliant (len(current_line) < 42):
			if len(current_first_line) < 42:
				# Log:
				##log.warning(f"First line non compliant; Will return to line 1.")
				# Update self.line_number, self.first_line and self.byte_offset:
				self.line_number = 1
				self.first_line = r"new file"
				self.byte_offset = 0
				# Return:
				if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
					cursor.close()
				return (1, r"new file")
			# If first line is different than what was on memory (DB, or self.first_line):
			if current_first_line != self.first_line:
				# Log:
				log.warning(f"The first line of the file \"{self.file_path}\" has changed.\nThe file was reset!")
				# Update self.line_number, self.first_line and self.byte_offset:
				self.line_number = 1
				self.first_line = r"new file"
				self.byte_offset = 0
				# Return:
				if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
					cursor.close()
				return (1, r"new file")

			# Iterate until the target line:
			byte_offset_before_reading = cursor.tell()
			while current_line_number < target_line_number:
				byte_offset_before_reading = cursor.tell()
				cursor.readline()
				# If the cursor hasn't moved forward at least 42:
				if(
					current_line_number + 1 != target_line_number
					and
					cursor.tell() < current_byte_offset + 42
				):
					# Log:
					log.warning(f"The cursor has reached the EOF before the target line number {target_line_number}")
					# Update self.line_number, self.first_line and self.byte_offset:
					self.line_number = 1
					self.first_line = r"new file"
					self.byte_offset = 0
					# Return:
					if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
						cursor.close()
					return (1, r"new file")
				current_byte_offset = cursor.tell()
				current_line_number += 1
			
			# Log:
			log.info(f"Cursor for file \"{self.file_path}\" was restored.\nReady to read at byte offset: {byte_offset_before_reading}, line number: {current_line_number}\nFirst line is \"{current_first_line}\"")
			# Update self.line_number, self.first_line and self.byte_offset:
			self.line_number = current_line_number
			self.first_line = current_first_line
			self.byte_offset = byte_offset_before_reading
			# Return:
			if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
				cursor.close()
			return (current_line_number, current_first_line)

		except Exception:
			# In case of file error or reset
			log.warning(f"File \"{self.file_path}\" can't restore its cursor to line {target_line_number}\n{traceback.format_exc()}")
			if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
				cursor.close()
			return (0, self.first_line)

	def read_next(self) -> tuple[bool, Event | None]:
		"""
		<h1>read_next</h1>
		Reads next line of the audit file.

		Returns:
			Tuple of
			bool: Wether or not it should continue reading:
			- True, if there are still lines left to read,
			- False, if there are no more lines to read.
			
			And an Event object or None

		Side Effects:
			Updates self.line_number, self.first_line (in case the file was reset), and self.byte_offset.
		"""

		##log.debug(f"self.byte_offset: {self.byte_offset}")

		# Open the file:
		try:
			cursor = open(self.file_path, 'r', encoding='utf-8')
		except:
			# If file was considered okay:
			if self.file_ok:
				log.warning(f"Failure to open file \"{self.file_path}\"")
				self.file_ok = False
			if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
				cursor.close()
			return (False, None)

		#continue_reading = False
		#event = Event(0, 0, None, 0, 0, True, 0)

		# Check first line to know if the file was reset:
		current_first_line: str = r"new file"
		current_byte_offset: int = 0
		current_line_number: int = 1
		try:
			# Put the cursor at the beginning of the file:
			cursor.seek(current_byte_offset)

			# Read first line:
			current_first_line = cursor.readline().strip()
			current_byte_offset = cursor.tell()
			current_line_number = 2

			# If it was assumed to be a new file (self.first_line == r"new file" or self.line_number == 1):
			if self.first_line == r"new file" or self.line_number == 1:
				# If indeed, there is already a first line:
				##log.debug(f"File was considered to be new. There are already new lines!")

				#log.debug(f"file {self.file_path}, {self.line_number} -> {self.first_line}")

				if len(current_first_line) > 42:
					# Updates self.line_number, self.first_line, self.byte_offset
					self.line_number = current_line_number
					self.first_line = current_first_line
					self.byte_offset = current_byte_offset
					# Check if there are more lines:
					cursor.readline()
					if cursor.tell() < current_byte_offset + 42:
						# If the next line is not up to specifications:
						if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
							cursor.close()
						return(False, Event(current_first_line, self.timezone, self.path_prefix_to_ignore))
					else:
						# If the next line is present and up to specifications:
						if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
							cursor.close()
						return(True, Event(current_first_line, self.timezone, self.path_prefix_to_ignore))
				else:
					# In case no lines at all are present:
					# Updates self.line_number, self.first_line, self.byte_offset
					self.line_number = 1
					self.first_line = r"new file"
					self.byte_offset = 0
					if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
						cursor.close()
					return (False, None)
			 # If current first line is too short or is different from what's in memory:
			elif len(current_first_line) < 42 or current_first_line != self.first_line:
				# File has been reset.
				log.info(f"File \"{self.file_path}\" has been reset.")
				self.line_number = 1
				self.first_line = r"new file"
				self.byte_offset = 0
				if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
					cursor.close()
				return (False, None)
			 # Finally, if the file was not reset:
			else:
				##log.debug(f"Reading {self.file_path}, at line {self.line_number}\nself.byte_offset: {self.byte_offset}")
				# Go to its current line (seek is faster than goto_line)
				cursor.seek(self.byte_offset)
				# Check to see if file_cursor indeed went to byte_offset
				if cursor.tell() != self.byte_offset:
					# If not, file is not OK
					if self.file_ok:
						log.warning(f"File \"{self.file_path}\" is not OK!")
					self.file_ok = False
					# Do not update self.line_number, self.first_line, self.byte_offset
					# Just return:
					if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
						cursor.close()
					return (False, None)
				else:
					# Actually read the next line:
					current_line: str = cursor.readline().strip()
					# If the read line is too short:
					if len(current_line) < 42:
						# It means there are no new lines worth reading
						# Do not update self.line_number, self.first_line, self.byte_offset
						# Just return:
						##log.debug(f"New line detected, but was too short:\n{current_line}")
						if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
							cursor.close()
						return (False, None)
					else:
						# Update self.line_number, no need to update self.first_line, self.byte_offset
						self.line_number += 1
						self.byte_offset = cursor.tell()
						# Now we just need to check if there are other lines ahead:
						
						cursor.readline()
						
						if cursor.tell() < self.byte_offset + 42:
							# If the next line is not up to specifications:
							if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
								cursor.close()
							return(False, Event(current_line, self.timezone, self.path_prefix_to_ignore))
						else:
							# If the next line is present and up to specifications:
							if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
								cursor.close()
							return(True, Event(current_line, self.timezone, self.path_prefix_to_ignore))

		except Exception:
			# In case of file error
			log.warning(f"Failure to read line from \"{self.file_path}\"")
			self.file_ok = False
			if 'cursor' in locals() and isinstance(cursor, io.IOBase) and not cursor.closed:
				cursor.close()
			return (False, None)

import traceback
import logging
log = logging.getLogger('root')


import sqlite3
import threading

class DB:
	def __init__(self):
		# Open DB in autocommit mode (isolation_level=None):
		self.connection = sqlite3.connect('include/db.sqlite3', isolation_level=None)
		# This is so that results from queries can be accessed like a list of dictionaries:
		self.connection.row_factory = sqlite3.Row
		# 'journal' in mode 'WAL':
		self.connection.execute('pragma journal_mode=wal;')
		self.cursor = self.connection.cursor()
		#log.debug(f"DB connection opened in thread id {threading.current_thread().ident}")

	def __del__(self):
		self.cursor.close()
		self.connection.close()
		#log.debug(f"DB connection closed in thread id {threading.current_thread().ident}")


	def query(self, query_string):
		result = None
		self.cursor.execute('BEGIN')
		try:
			result = self.cursor.execute(query_string).fetchall()
		except Exception as e:
			self.connection.rollback()
			log.error(f"Error executing query:\n{query_string}\n{traceback.format_exc()}")
			#Do not raise
		else:
			self.connection.commit()
			return result

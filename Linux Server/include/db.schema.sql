BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS "Audit_Files" (
	"file_id"	INTEGER,
	"file_path"	TEXT NOT NULL UNIQUE COLLATE BINARY,
	"line_number"	INTEGER,
	"first_line"	TEXT COLLATE BINARY,
	PRIMARY KEY("file_id")
);

CREATE TABLE IF NOT EXISTS "Users" (
	"user_id"	INTEGER,
	"user_name"	TEXT NOT NULL COLLATE NOCASE,
	"user_host"	TEXT NOT NULL COLLATE NOCASE,
	"user_ip"	TEXT NOT NULL COLLATE NOCASE,
	PRIMARY KEY("user_id"),
	UNIQUE("user_name","user_host","user_ip")
);

CREATE TABLE IF NOT EXISTS "Shares" (
	"share_id"	INTEGER,
	"share_name"	TEXT NOT NULL COLLATE BINARY,
	"share_host"	TEXT NOT NULL COLLATE BINARY,
	"share_path"	TEXT NOT NULL COLLATE BINARY,
	PRIMARY KEY("share_id"),
	UNIQUE("share_name","share_host")
);

CREATE TABLE IF NOT EXISTS "Nodes" (
	"node_id"	INTEGER,
	"node_path"	TEXT NOT NULL COLLATE BINARY,
	"share_id"	INTEGER NOT NULL,
	"node_name"	TEXT NOT NULL COLLATE NOCASE,
	PRIMARY KEY("node_id"),
	UNIQUE("node_path","share_id"),
	FOREIGN KEY("share_id") REFERENCES "Shares"("share_id")
);

CREATE TABLE IF NOT EXISTS "Events" (
	"event_id"	INTEGER,
	"user_id"	INTEGER NOT NULL,
	"share_id"	INTEGER NOT NULL,
	"node1_id"	INTEGER NOT NULL,
	"node2_id"	INTEGER,
	"utc_timestamp"	INTEGER NOT NULL,
	"event_type"	INTEGER NOT NULL,
	PRIMARY KEY("event_id"),
	FOREIGN KEY("user_id") REFERENCES "Users"("user_id"),
	FOREIGN KEY("node1_id") REFERENCES "Nodes"("node_id"),
	FOREIGN KEY("node2_id") REFERENCES "Nodes"("node_id"),
	FOREIGN KEY("share_id") REFERENCES "Shares"("share_id")
);

COMMIT;

/*
BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Users" (
	"user_id"	INTEGER,
	"user_name"	TEXT NOT NULL COLLATE NOCASE,
	"user_host"	TEXT NOT NULL COLLATE NOCASE,
	"user_ip"	TEXT NOT NULL COLLATE NOCASE,
	PRIMARY KEY("user_id"),
	UNIQUE("user_name","user_host","user_ip")
);
CREATE TABLE IF NOT EXISTS "Audit_Files" (
	"file_id"	INTEGER,
	"file_path"	TEXT NOT NULL UNIQUE COLLATE BINARY,
	"line_number"	INTEGER,
	"first_line"	TEXT COLLATE BINARY,
	PRIMARY KEY("file_id")
);
CREATE TABLE IF NOT EXISTS "Events" (
	"event_id"	INTEGER,
	"user_id"	INTEGER NOT NULL,
	"share_id"	INTEGER NOT NULL,
	"node1_id"	INTEGER NOT NULL,
	"node2_id"	INTEGER,
	"utc_timestamp"	INTEGER NOT NULL,
	"event_type"	INTEGER NOT NULL,
	PRIMARY KEY("event_id"),
	FOREIGN KEY("user_id") REFERENCES "Users"("user_id"),
	FOREIGN KEY("node1_id") REFERENCES "Nodes"("node_id"),
	FOREIGN KEY("node2_id") REFERENCES "Nodes"("node_id"),
	FOREIGN KEY("share_id") REFERENCES "Shares"("share_id")
);
CREATE TABLE IF NOT EXISTS "Nodes" (
	"node_id"	INTEGER,
	"node_path"	TEXT NOT NULL COLLATE BINARY,
	"share_id"	INTEGER NOT NULL,
	"node_name"	TEXT NOT NULL COLLATE NOCASE,
	PRIMARY KEY("node_id"),
	UNIQUE("node_path","share_id"),
	FOREIGN KEY("share_id") REFERENCES "Shares"("share_id")
);
CREATE TABLE IF NOT EXISTS "Shares" (
	"share_id"	INTEGER,
	"share_name"	TEXT NOT NULL COLLATE BINARY,
	"share_host"	TEXT NOT NULL COLLATE BINARY,
	"share_path"	TEXT NOT NULL COLLATE BINARY,
	PRIMARY KEY("share_id"),
	UNIQUE("share_name","share_host")
);
COMMIT;
*/
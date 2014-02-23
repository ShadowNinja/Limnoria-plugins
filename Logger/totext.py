#!/usr/bin/env python3

import sys
import time
from storage import LogDB

if len(sys.argv) != 5:
	print("""Usage:
	%s <LogDB> <Network> <Channel> <Time>
	""" % sys.argv[0])
	sys.exit(1)

db = LogDB(sys.argv[1])

msgstrs = [
	"<{nick}> {message}",
	"-{nick}- {message}",
	"-*- {nick} {message}",
	"--> {nick} has joined",
	"<-- {nick} has parted ({message})",
	"<-- {nick} has quit ({message})",
	"*** {nick} has been kicked {message}",
	"<-> {nick} is now known as {message}",
	"*** Mode [{message}] by {nick}",
	"*** Topic set by {nick} to {message}"
]

def msgToStr(mtype, nick, msg):
	return msgstrs[mtype].format(nick=nick, message=msg)

latest = db.cur.execute("SELECT timestamp FROM log ORDER BY id DESC LIMIT 1").fetchone()[0]
buf = db.getBuffer(sys.argv[2], sys.argv[3])
log = db.get(buf["id"], latest - int(sys.argv[4]), int(sys.argv[4]))

for message in log:
	tm = time.strftime("[%H:%M:%S] ", time.gmtime(message["timestamp"]))
	print(tm + msgToStr(message["type"], message["nick"], message["message"]))


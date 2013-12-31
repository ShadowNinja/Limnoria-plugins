import json
import socket
import time
import math
import random
import supybot.callbacks as callbacks
from supybot.commands import *
import supybot.ircdb as ircdb
import supybot.utils as utils


class Minetest(callbacks.Plugin):
	"""Adds some Minetest-related commands
	"""

	thteaded = True

	def up(self, irc, msg, args, address, portlist):
		"""address [ports]

		Checks if a Minetest server is up.
		Ports can be in the format port1,port2,port3-port5."""
		if address == None:
			irc.error("Give me a Server Address")
			return
		if not '.' in address:
			irc.error("Invalid Address")
			return

		if ':' in address:
			try:
				ports = [int(address.split(":")[1])]
			except ValueError: #The string couldn't be converted to an int
				irc.reply("Invalid usage, see help Minetest up")
				return
			address = address.split(":")[0]
		elif portlist is None:
			ports = [30000]
		else:
			ports = self.getPorts(portlist, irc)
		if ports == None:
			return

		if len(ports) != 1 and irc.isChannel(msg.args[0]):
			irc.reply("To check multiple Ports please use Query")
			return
		if len(ports) > 6:
			irc.error("Too many Ports specified")
			return

		for port in ports:
			message = self.ServerUp(address, port)
			if message:
				irc.reply(message)
			else:
				irc.reply("Error: Maybe you typed the address wrong?")
	up = wrap(up, ['something', optional('something')])



	def server(self, irc, msg, args, options):
		'''[--{name,address,players,ping,port} <value>]

		On numeric options like 'ping', 'port' and 'players' <value> can be  num, <num, >num, !num, highest, or lowest.
		'''
		data = utils.web.getUrl("http://servers.minetest.net/list")
		server_list = json.loads(data.decode("UTF-8"))["list"]

		#Run through every filter suplied while we have a result
		for option in options:
			if len(server_list) > 0:
				server_list = self.serverSearchFilters[option[0]]\
						(self, server_list, option[1])

		if len(server_list) == 0:
			irc.reply("No results.")
			return

		choice = random.randrange(0, len(server_list))

		server = server_list[choice]

		clients = str(server["clients"]) + "/" + str(server["clients_top"])

		address = server["address"]
		if not server["port"] == "30000":
			address = address + " | Port: " + server["port"]

		irc.reply("%s | %s | Clients: %s | Version: %s | Ping: %s" %\
		         (server["name"], address, clients, server["version"], server["ping"]))

	server = wrap(server, [getopts({
			#Number values are "something" to allow for <, !, highest, etc.
			"name":    "something",
			"address": "something",
			"version": "something",
			"game":    "something",
			"players": "something",
			"ping":    "something",
			"port":    "something"
		})])


	# Helpers

	def filterServersByName(self, server_list, arg, field):
		result = []
		for i in range(len(server_list)):
			if arg.lower().strip()\
			   in server_list[i][field].lower().strip():
				result.append(server_list[i])
		return result

	def filterServersByNum(self, server_list, arg, field, typeconv):
		result = []
		if arg.startswith("<"): # less comparing
			try: num = typeconv(arg[1:])
			except: return
			for i in range(0, len(server_list)):
				if typeconv(server_list[i][field]) < num:
					result.append(server_list[i])
		elif arg.startswith(">"): # more comparing
			try: num = typeconv(arg[1:])
			except: return
			for i in range(0, len(server_list)):
				if typeconv(server_list[i][field]) > num:
					result.append(server_list[i])
		elif arg.startswith("!"): # NOT
			try: num = typeconv(arg[1:])
			except: return
			for i in range(0, len(server_list)):
				if typeconv(server_list[i][field]) != num:
					result.append(server_list[i])
		elif arg == "highest":
			highest = [0, 0]
			for i in range(0, len(server_list)):
				if typeconv(server_list[i][field]) > highest[0]:
					highest[0] = typeconv(server_list[i][field])
					highest[1] = i
			result = [server_list[highest[1]]]
		elif arg == "lowest":
			lowest = [None, 0]
			for i in range(0, len(server_list)):
				if lowest[0] is None or\
				   typeconv(server_list[i][field]) < lowest[0]:
					lowest[0] = typeconv(server_list[i][field])
					lowest[1] = i
			result = [server_list[lowest[1]]]
		else:
			try: num = typeconv(arg)
			except: return server_list
			for i in range(len(server_list)):
				if typeconv(server_list[i][field]) == num:
					result.append(server_list[i])
		return result

	serverSearchFilters = {
		"address": lambda self, server_list, arg: self.filterServersByName(server_list, arg, "address"),
		"name":    lambda self, server_list, arg: self.filterServersByName(server_list, arg, "name"),
		"version": lambda self, server_list, arg: self.filterServersByName(server_list, arg, "version"),
		"game":    lambda self, server_list, arg: self.filterServersByName(server_list, arg, "gameid"),

		"players": lambda self, server_list, arg: self.filterServersByNum(server_list, arg, "clients", int),
		"ping":    lambda self, server_list, arg: self.filterServersByNum(server_list, arg, "ping", float),
		"port":    lambda self, server_list, arg: self.filterServersByNum(server_list, arg, "port", int)
	}

	def ServerUp(self, address, port):
		repres = address + ':' + str(port)
		try:
			start = time.time()
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.settimeout(2.5)
			buf = b'\x4f\x45\x74\x03\x00\x00\x00\x01'
			sock.sendto(buf, (address, port))
			data, addr = sock.recvfrom(1000)
			if data:
				peer_id = data[12:14]
				buf = b'\x4f\x45\x74\x03' + peer_id + b'\x00\x00\x03'
				sock.sendto(buf, (address, port))
				sock.close()
				end = time.time()
				return "%s is up (%dms)" % (repres,int((end-start)*1000))
			else:
				return "%s seems to be down " % repres
		except socket.timeout:
			return "%s seems to be down " % repres
		except:
			return None

	def getPorts(self, port, irc):
		if '-' in port or ',' in port:
			ports = []
			ports_ = port.split(',')
			for p in ports_:
				if '-' in p:
					if len(p.split('-')) != 2:
						irc.error("Invalid Port List")
						return None
					else:
						try:
							a = int(p.split('-')[0])
						except:
							irc.error("Invalid Port: %s" % p.split('-')[0])
							return None
						try:
							b = int(p.split('-')[1]) + 1
						except:
							irc.error("Invalid Port: %s" % p.split('-')[1])
							return None
						for i in range(a, b):
							ports.append(i)
				else:
					try:
						ports.append(int(p))
					except:
						irc.error("Invalid Port: %s" % p)
						return None
		else:
			try:
				ports = [int(port)]
			except:
				irc.error("Invalid port")
				return None
		return ports

Class = Minetest


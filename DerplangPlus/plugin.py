
from . import derplang
import multiprocessing
import supybot.callbacks as callbacks
from supybot.commands import *

def derplangWrapper(code, pipe):
	try:
		env = derplang.run(code, limit = 1000)
		pipe.send(env)
		pipe.close()
	except derplang.DerplangError as err:
		pipe.send(err)
		pipe.close()

class DerplangPlus(callbacks.Plugin):
	"""Runs a Derplang+ program
	"""
	threaded = True
	def derplangplus(self, irc, msg, args, code):
		"""<code>

		Runs Derplang+ code"""
		(PPipe, CPipe) = multiprocessing.Pipe()
		proc = multiprocessing.Process(target = derplangWrapper,
				args = (code, CPipe))
		try:
			proc.start()
			proc.join(1)  # One second timeout
			if proc.is_alive():
				proc.terminate()
				raise multiprocessing.TimeoutError
			env = PPipe.recv()
			if isinstance(env, derplang.DerplangError):
				raise env
		except derplang.DerplangError as err:
			irc.reply("Derplang error: " + str(err))
			return
		except multiprocessing.TimeoutError:
			irc.reply("The script timed out.")
			return
		finally:
			del proc

		if env["output"] == "":
			irc.replySuccess()
		else:
			irc.reply(env["output"])
	derplangplus = wrap(derplangplus, ['something'])

Class = DerplangPlus


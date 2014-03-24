import supybot.callbacks as callbacks
from supybot.commands import *

class Util(callbacks.Plugin):
	"""
	Custom utility commands
	"""

	def stripto(self, irc, msg, args, delim, s):
		"""<delemiter> <string>

		Returns the portion of string before the first occurance of delemiter.
		"""
		pos = s.find(delim)
		if pos >= 0:
			irc.reply(s[0:pos])
		else:
			irc.error("Delemiter not found.")
	stripto = wrap(stripto, ["something", "text"])

Class = Util

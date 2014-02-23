import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
	from supybot.questions import expect, anything, something, yn
	conf.registerPlugin('Logger', True)


Logger = conf.registerPlugin('Logger')

conf.registerChannelValue(Logger, "enable",
	registry.Boolean(True, """Determines whether logging is enabled."""))


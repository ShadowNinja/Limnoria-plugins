from __future__ import division

import time

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('FloodProtector')

def configure(advanced):
	from supybot.questions import output, expect, anything, something, yn
	conf.registerPlugin('FloodProtector', True)

FloodProtector = conf.registerPlugin('FloodProtector')

conf.registerChannelValue(FloodProtector, "enabled",
	registry.Boolean(True, "Whether to check floods in the channel."))

# vim:set textwidth=79:

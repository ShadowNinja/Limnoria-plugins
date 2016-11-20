
"""
Sends a message to an op when then ban or quiet someone.
"""

import supybot
import supybot.world as world

__version__ = "0.1.0"

__author__ = supybot.Author("Owen", "ShadowNinja", "shadowninja@minetest.net")

__contributors__ = {}

from . import config
from . import plugin
from imp import reload
reload(plugin) # In case we're being reloaded.
reload(config)

Class = plugin.Class
configure = config.configure


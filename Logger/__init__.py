
"""
An SQLite3 channel logger
"""

import supybot
import supybot.world as world

# Use this for the version of this plugin.  You may wish to put a CVS keyword
# in here if you're keeping the plugin in CVS or some similar system.
__version__ = ""

__author__ = supybot.Author("Owen", "ShadowNinja", "shadowninja@minetest.net")

# This is a dictionary mapping supybot.Author instances to lists of
# contributions.
__contributors__ = {}

from . import config
from . import storage
from . import server
from . import plugin
from imp import reload
# In case we're being reloaded.
reload(config)
reload(storage)
reload(server)
reload(plugin)

if world.testing:
	from . import test

Class = plugin.Class
configure = config.configure


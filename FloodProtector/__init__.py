"""
Protects against various forms of flooding.
"""

import supybot

# Use this for the version of this plugin.  You may wish to put a CVS keyword
# in here if you're keeping the plugin in CVS or some similar system.
__version__ = ""

__author__ = supybot.Author("Owen", "ShadowNinja", "shadowninja@minetest.net")

# This is a dictionary mapping supybot.Author instances to lists of
# contributions.
__contributors__ = {}

from . import config
from . import plugin
from imp import reload
# In case we're being reloaded.
reload(plugin)
reload(config)

Class = plugin.Class
configure = config.configure

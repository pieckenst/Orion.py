"""
Discord API Wrapper
~~~~~~~~~~~~~~~~~~~

A basic wrapper for the Discord API.

:copyright: (c) 2015-present Rapptz
:license: MIT, see LICENSE for more details.

"""

__title__ = 'fusion'
__author__ = 'Benitz'
__license__ = 'MIT'
__copyright__ = 'Copyright 2021-present Benitz'
__version__ = '2.2.5'

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

import logging
from typing import Literal, NamedTuple

from . import abc, opus, ui, utils
from .activity import *
from .appinfo import *
from .asset import *
from .audit_logs import *
from .channel import *
from .client import *
from .colour import *
from .components import *
from .embeds import *
from .emoji import *
from .enums import *
from .errors import *
from .file import *
from .flags import *
from .guild import *
from .integrations import *
from .interactions import *
from .invite import *
from .member import *
from .mentions import *
from .message import *
from .object import *
from .partial_emoji import *
from .permissions import *
from .player import *
from .raw_models import *
from .reaction import *
from .role import *
from .shard import *
from .stage_instance import *
from .sticker import *
from .team import *
from .template import *
from .threads import *
from .user import *
from .voice_client import *
from .webhook import *
from .widget import *
#from .timestamp import *
#for whatever reason it's a star import issue
#you can do from .timestamp import TimeStamp like from 
"from .timestamp import TimeStamp"
#but it doesn't allow *

class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


version_info: VersionInfo = VersionInfo(major=2, minor=2, micro=5, releaselevel='alpha', serial=0)

logging.getLogger(__name__).addHandler(logging.NullHandler())

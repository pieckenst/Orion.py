"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import re
import copy
import asyncio
import logging
import signal
import sys
import traceback
import discord
import typing

from contextlib import suppress
from inspect import getdoc, iscoroutinefunction
from typing import Any, Callable, Coroutine, Dict, Generator, List, Optional, Sequence, TYPE_CHECKING, Tuple, TypeVar, Union
from .ext.commands import AutoShardedBot, Bot, Cog

import aiohttp

from . import context, error, http, model, Forbidden, HTTPException, Guild, NotFound
from .user import User, ClientUser
from .invite import Invite
from .template import Template
from .widget import Widget
from .guild import Guild
from .emoji import Emoji
from .channel import _threaded_channel_factory, PartialMessageable
from .enums import ChannelType
from .mentions import AllowedMentions
from .errors import *
from .enums import Status, VoiceRegion
from .flags import ApplicationFlags, Intents
from .gateway import *
from .activity import ActivityTypes, BaseActivity, create_activity
from .voice_client import VoiceClient
from .http import HTTPClient
from .state import ConnectionState
from . import utils
from .utils import MISSING
from .object import Object
from .backoff import ExponentialBackoff
from .webhook import Webhook
from .iterators import GuildIterator
from .appinfo import AppInfo
from .ui.view import View
from .stage_instance import StageInstance
from .threads import Thread
from .sticker import GuildSticker, StandardSticker, StickerPack, _sticker_factory
from .InteractionUtils import manage_commands
from .InteractionUtils.manage_components import get_components_ids, get_messages_ids

if TYPE_CHECKING:
    from .abc import SnowflakeTime, PrivateChannel, GuildChannel, Snowflake
    from .channel import DMChannel
    from .message import Message
    from .member import Member
    from .voice_client import VoiceProtocol

__all__ = (
    'Client',
)

def _get_val(d: dict, key):
    try:
        value = d[key]
    except KeyError:
        value = d[None]
    return value

Coro = TypeVar('Coro', bound=Callable[..., Coroutine[Any, Any, Any]])


_log = logging.getLogger(__name__)

def _cancel_tasks(loop: asyncio.AbstractEventLoop) -> None:
    tasks = {t for t in asyncio.all_tasks(loop=loop) if not t.done()}

    if not tasks:
        return

    _log.info('Cleaning up after %d tasks.', len(tasks))
    for task in tasks:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    _log.info('All tasks finished cancelling.')

    for task in tasks:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'Unhandled exception during Client.run shutdown.',
                'exception': task.exception(),
                'task': task
            })

def _cleanup_loop(loop: asyncio.AbstractEventLoop) -> None:
    try:
        _cancel_tasks(loop)
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        _log.info('Closing the event loop.')
        loop.close()

class Interaction:
    """
    command interaction handler class.
    :param client: discord.py Client or Bot instance.
    :type client: Union[discord.Client, discord.ext.commands.Bot]
    :param sync_commands: Whether to sync commands automatically. Default `False`.
    :type sync_commands: bool
    :param debug_guild: Guild ID of guild to use for testing commands. Prevents setting global commands in favor of guild commands, which update instantly
    :type debug_guild: int
    :param delete_from_unused_guilds: If the bot should make a request to set no commands for guilds that haven't got any commands registered in :class:``Interaction``. Default `False`.
    :type delete_from_unused_guilds: bool
    :param sync_on_cog_reload: Whether to sync commands on cog reload. Default `False`.
    :type sync_on_cog_reload: bool
    :param override_type: Whether to override checking type of the client and try register event.
    :type override_type: bool
    :param application_id: The application id of the bot, required only when the application id and bot id are different. (old bots)
    :type application_id: int
    .. note::
        If ``sync_on_cog_reload`` is enabled, command syncing will be triggered when :meth:`discord.ext.commands.Bot.reload_extension`
        is triggered.
    :ivar _discord: Discord client of this client.
    :ivar commands: Dictionary of the registered commands via :func:`.slash` decorator.
    :ivar menu_commands: Dictionary of the registered context menus via the :func:`.context_menu` decorator.
    :ivar req: :class:`.http.InteractionRequest` of this client.
    :ivar logger: Logger of this client.
    :ivar sync_commands: Whether to sync commands automatically.
    :ivar sync_on_cog_reload: Whether to sync commands on cog reload.
    :ivar has_listener: Whether discord client has listener add function.
    """

    def __init__(
        self,
        client: typing.Union[Client, Bot],
        sync_commands: bool = False,
        debug_guild: typing.Optional[int] = None,
        delete_from_unused_guilds: bool = False,
        sync_on_cog_reload: bool = False,
        override_type: bool = False,
        application_id: typing.Optional[int] = None,
    ):
        self._discord = client
        self.commands = {"context": {}}
        self.subcommands = {}
        self.components = {}
        self.logger = logging.getLogger("orion.py")
        self.req = http.InteractionRequest(self.logger, self._discord, application_id)
        self.sync_commands = sync_commands
        self.debug_guild = debug_guild
        self.sync_on_cog_reload = sync_on_cog_reload

        if self.sync_commands:
            self._discord.loop.create_task(self.sync_all_commands(delete_from_unused_guilds))

        if (
            not isinstance(client, Bot)
            and not isinstance(client, AutoShardedBot)
            and not override_type
        ):
            self.logger.warning(
                "Detected discord.Client! It is highly recommended to use `commands.Bot`. Do not add any `on_socket_response` event."
            )

            self._discord.on_socket_response = self.on_socket_response
            self.has_listener = False
        else:
            if not hasattr(self._discord, "slash"):
                self._discord.slash = self
            else:
                raise error.DuplicateSlashClient("You can't have duplicate Interaction instances!")

            self._discord.add_listener(self.on_socket_response)
            self.has_listener = True
            default_add_function = self._discord.add_cog

            def override_add_cog(cog: Cog):
                default_add_function(cog)
                self.get_cog_commands(cog)

            self._discord.add_cog = override_add_cog
            default_remove_function = self._discord.remove_cog

            def override_remove_cog(name: str):
                cog = self._discord.get_cog(name)
                if cog is None:
                    return
                self.remove_cog_commands(cog)
                default_remove_function(name)

            self._discord.remove_cog = override_remove_cog

            if self.sync_on_cog_reload:
                orig_reload = self._discord.reload_extension

                def override_reload_extension(*args):
                    orig_reload(*args)
                    self._discord.loop.create_task(
                        self.sync_all_commands(delete_from_unused_guilds)
                    )

                self._discord.reload_extension = override_reload_extension

    def get_cog_commands(self, cog: Cog):
        """
        Gets command interaction from :class:`discord.ext.commands.Cog`.
        .. note::
            Since version ``1.0.9``, this gets called automatically during cog initialization.
        :param cog: Cog that has command interactions.
        :type cog: discord.ext.commands.Cog
        """
        if hasattr(cog, "_slash_registered"):
            return self.logger.warning(
                "Calling get_cog_commands is no longer required "
                "to add cog command interactions. Make sure to remove all calls to this function."
            )
        cog._slash_registered = True
        func_list = [getattr(cog, x) for x in dir(cog)]

        self._get_cog_interactions(cog, func_list)
        self._get_cog_component_callbacks(cog, func_list)

    def _get_cog_interactions(self, cog, func_list):
        res = [
            x
            for x in func_list
            if isinstance(x, (model.CogBaseCommandObject, model.CogSubcommandObject))
        ]

        for x in res:
            x.cog = cog
            if isinstance(x, model.CogBaseCommandObject):
                if x.name in self.commands:
                    raise error.DuplicateCommand(x.name)
                self.commands[x.name] = x
            else:
                if x.base in self.commands:
                    base_command = self.commands[x.base]
                    for i in x.allowed_guild_ids:
                        if i not in base_command.allowed_guild_ids:
                            base_command.allowed_guild_ids.append(i)

                    base_permissions = x.base_command_data["api_permissions"]
                    if base_permissions:
                        for applicable_guild in base_permissions:
                            if applicable_guild not in base_command.permissions:
                                base_command.permissions[applicable_guild] = []
                            base_command.permissions[applicable_guild].extend(
                                base_permissions[applicable_guild]
                            )

                    self.commands[x.base].has_subcommands = True

                else:
                    self.commands[x.base] = model.BaseCommandObject(x.base, x.base_command_data)
                if x.base not in self.subcommands:
                    self.subcommands[x.base] = {}
                if x.subcommand_group:
                    if x.subcommand_group not in self.subcommands[x.base]:
                        self.subcommands[x.base][x.subcommand_group] = {}
                    if x.name in self.subcommands[x.base][x.subcommand_group]:
                        raise error.DuplicateCommand(f"{x.base} {x.subcommand_group} {x.name}")
                    self.subcommands[x.base][x.subcommand_group][x.name] = x
                else:
                    if x.name in self.subcommands[x.base]:
                        raise error.DuplicateCommand(f"{x.base} {x.name}")
                    self.subcommands[x.base][x.name] = x

    def _get_cog_component_callbacks(self, cog, func_list):
        res = [x for x in func_list if isinstance(x, model.CogComponentCallbackObject)]

        for x in res:
            x.cog = cog
            self._add_comp_callback_obj(x)

    def remove_cog_commands(self, cog):
        """
        Removes command interaction from :class:`discord.ext.commands.Cog`.
        .. note::
            Since version ``1.0.9``, this gets called automatically during cog de-initialization.
        :param cog: Cog that has command interactions.
        :type cog: discord.ext.commands.Cog
        """
        if hasattr(cog, "_slash_registered"):
            del cog._slash_registered
        func_list = [getattr(cog, x) for x in dir(cog)]
        self._remove_cog_interactions(func_list)
        self._remove_cog_component_callbacks(func_list)

    def _remove_cog_interactions(self, func_list):
        res = [
            x
            for x in func_list
            if isinstance(x, (model.CogBaseCommandObject, model.CogSubcommandObject))
        ]
        for x in res:
            if isinstance(x, model.CogBaseCommandObject):
                if x.name not in self.commands:
                    continue
                if x.name in self.subcommands:
                    self.commands[x.name].func = None
                    continue
                del self.commands[x.name]
            else:
                if x.base not in self.subcommands:
                    continue
                if x.subcommand_group:
                    del self.subcommands[x.base][x.subcommand_group][x.name]
                    if not self.subcommands[x.base][x.subcommand_group]:
                        del self.subcommands[x.base][x.subcommand_group]
                else:
                    del self.subcommands[x.base][x.name]
                if not self.subcommands[x.base]:
                    del self.subcommands[x.base]
                    if x.base in self.commands:
                        if self.commands[x.base].func:
                            self.commands[x.base].has_subcommands = False
                        else:
                            del self.commands[x.base]

    def _remove_cog_component_callbacks(self, func_list):
        res = [x for x in func_list if isinstance(x, model.CogComponentCallbackObject)]

        for x in res:
            self.remove_component_callback_obj(x)

    async def to_dict(self):
        """
        Converts all commands currently registered to :class:`Interaction` to a dictionary.
        Returns a dictionary in the format:
        .. code-block:: python
            {
                "global" : [], # list of global commands
                "guild" : {
                    0000: [] # list of commands in the guild 0000
                }
            }
        Commands are in the format specified by discord `here <https://discord.com/developers/docs/interactions/slash-commands#applicationcommand>`_
        """
        await self._discord.wait_until_ready()
        all_guild_ids = []
        for x in self.commands:
            if x == "context":
                for _x in self.commands["context"]:
                    _selected = self.commands["context"][_x]
                    for i in _selected.allowed_guild_ids:
                        if i not in all_guild_ids:
                            all_guild_ids.append(i)
                continue
            for i in self.commands[x].allowed_guild_ids:
                if i not in all_guild_ids:
                    all_guild_ids.append(i)
        cmds = {"global": [], "guild": {x: [] for x in all_guild_ids}}
        wait = {}
        for x in self.commands:
            if x == "context":
                for _x in self.commands["context"]:
                    selected = self.commands["context"][_x]

                    if selected.allowed_guild_ids:
                        for y in selected.allowed_guild_ids:
                            if y not in wait:
                                wait[y] = {}
                            command_dict = {
                                "name": _x,
                                "options": selected.options or [],
                                "default_permission": selected.default_permission,
                                "permissions": {},
                                "type": selected._type,
                            }
                            if y in selected.permissions:
                                command_dict["permissions"][y] = selected.permissions[y]
                            wait[y][_x] = copy.deepcopy(command_dict)
                    else:
                        if "global" not in wait:
                            wait["global"] = {}
                        command_dict = {
                            "name": _x,
                            "options": selected.options or [],
                            "default_permission": selected.default_permission,
                            "permissions": selected.permissions or {},
                            "type": selected._type,
                        }
                        wait["global"][_x] = copy.deepcopy(command_dict)

                continue

            selected = self.commands[x]
            if selected.allowed_guild_ids:
                for y in selected.allowed_guild_ids:
                    if y not in wait:
                        wait[y] = {}
                    command_dict = {
                        "name": x,
                        "description": selected.description or "No Description.",
                        "options": selected.options or [],
                        "default_permission": selected.default_permission,
                        "permissions": {},
                        "type": selected._type,
                    }
                    if command_dict["type"] != 1:
                        command_dict.pop("description")
                    if y in selected.permissions:
                        command_dict["permissions"][y] = selected.permissions[y]
                    wait[y][x] = copy.deepcopy(command_dict)
            else:
                if "global" not in wait:
                    wait["global"] = {}
                command_dict = {
                    "name": x,
                    "description": selected.description or "No Description.",
                    "options": selected.options or [],
                    "default_permission": selected.default_permission,
                    "permissions": selected.permissions or {},
                    "type": selected._type,
                }
                if command_dict["type"] != 1:
                    command_dict.pop("description")
                wait["global"][x] = copy.deepcopy(command_dict)

        for x in self.commands:
            if x == "context":
                continue

            if not self.commands[x].has_subcommands:
                continue
            tgt = self.subcommands[x]
            for y in tgt:
                sub = tgt[y]
                if isinstance(sub, model.SubcommandObject):
                    _dict = {
                        "name": sub.name,
                        "description": sub.description or "No Description.",
                        "type": model.InteractionOptionType.SUB_COMMAND,
                        "options": sub.options or [],
                    }
                    if sub.allowed_guild_ids:
                        for z in sub.allowed_guild_ids:
                            wait[z][x]["options"].append(_dict)
                    else:
                        wait["global"][x]["options"].append(_dict)
                else:
                    queue = {}
                    base_dict = {
                        "name": y,
                        "description": "No Description.",
                        "type": model.InteractionOptionType.SUB_COMMAND_GROUP,
                        "options": [],
                    }
                    for z in sub:
                        sub_sub = sub[z]
                        _dict = {
                            "name": sub_sub.name,
                            "description": sub_sub.description or "No Description.",
                            "type": model.InteractionOptionType.SUB_COMMAND,
                            "options": sub_sub.options or [],
                        }
                        if sub_sub.allowed_guild_ids:
                            for i in sub_sub.allowed_guild_ids:
                                if i not in queue:
                                    queue[i] = copy.deepcopy(base_dict)
                                queue[i]["options"].append(_dict)
                        else:
                            if "global" not in queue:
                                queue["global"] = copy.deepcopy(base_dict)
                            queue["global"]["options"].append(_dict)
                    for i in queue:
                        wait[i][x]["options"].append(queue[i])

        for x in wait:
            if x == "global":
                [cmds["global"].append(n) for n in wait["global"].values()]
            else:
                [cmds["guild"][x].append(n) for n in wait[x].values()]

        return cmds

    async def enable_command_interactions(
        self, delete_from_unused_guilds=False, delete_perms_from_unused_guilds=False
    ):
        """
        Matches commands registered on Discord to commands registered here.
        Deletes any commands on Discord but not here, and registers any not on Discord.
        This is done with a `put` request.
        A PUT request will only be made if there are changes detected.
        If ``sync_commands`` is ``True``, then this will be automatically called.
        :param delete_from_unused_guilds: If the bot should make a request to set no commands for guilds that haven't got any commands registered in :class:``Interaction``
        :param delete_perms_from_unused_guilds: If the bot should make a request to clear permissions for guilds that haven't got any permissions registered in :class:``Interaction``
        """
        permissions_map = {}
        cmds = await self.to_dict()
        self.logger.info("Syncing command interactions...")
        cmds_formatted = {self.debug_guild: cmds["global"]}
        for guild in cmds["guild"]:
            cmds_formatted[guild] = cmds["guild"][guild]

        for scope in cmds_formatted:
            permissions = {}
            new_cmds = cmds_formatted[scope]
            existing_cmds = await self.req.get_all_commands(guild_id=scope)
            existing_by_name = {}
            to_send = []
            changed = False
            for cmd in existing_cmds:
                existing_by_name[cmd["name"]] = model.CommandData(**cmd)

            if len(new_cmds) != len(existing_cmds):
                changed = True

            for command in new_cmds:
                cmd_name = command["name"]
                permissions[cmd_name] = command.pop("permissions")
                if cmd_name in existing_by_name:
                    cmd_data = model.CommandData(**command)
                    existing_cmd = existing_by_name[cmd_name]
                    if cmd_data != existing_cmd:
                        changed = True
                        to_send.append(command)
                    else:
                        command_with_id = command
                        command_with_id["id"] = existing_cmd.id
                        to_send.append(command_with_id)
                else:
                    changed = True
                    to_send.append(command)

            if changed:
                self.logger.debug(
                    f"Detected changes on {scope if scope is not None else 'global'}, updating them"
                )
                try:
                    existing_cmds = await self.req.put_interactions(
                        interactions=to_send, guild_id=scope
                    )
                except HTTPException as ex:
                    if ex.status == 400:
                        cmd_nums = set(
                            re.findall(r"^[\w-]{1,32}$", ex.args[0])
                        )
                        error_string = ex.args[0]

                        for num in cmd_nums:
                            error_command = to_send[int(num)]
                            error_string = error_string.replace(
                                f"In {num}",
                                f"'{error_command.get('name')}'",
                            )

                        ex.args = (error_string,)

                    raise ex
            else:
                self.logger.debug(
                    f"Detected no changes on {scope if scope is not None else 'global'}, skipping"
                )

            id_name_map = {}
            for cmd in existing_cmds:
                id_name_map[cmd["name"]] = cmd["id"]

            for cmd_name in permissions:
                cmd_permissions = permissions[cmd_name]
                cmd_id = id_name_map[cmd_name]
                for applicable_guild in cmd_permissions:
                    if applicable_guild not in permissions_map:
                        permissions_map[applicable_guild] = []
                    permission = {
                        "id": cmd_id,
                        "guild_id": applicable_guild,
                        "permissions": cmd_permissions[applicable_guild],
                    }
                    permissions_map[applicable_guild].append(permission)

        self.logger.info("Syncing Interaction permissions...")
        self.logger.debug(f"Command permission data are {permissions_map}")
        for scope in permissions_map:
            existing_perms = await self.req.get_all_guild_commands_permissions(scope)
            new_perms = permissions_map[scope]

            changed = False
            if len(existing_perms) != len(new_perms):
                changed = True
            else:
                existing_perms_model = {}
                for existing_perm in existing_perms:
                    existing_perms_model[existing_perm["id"]] = model.GuildPermissionsData(
                        **existing_perm
                    )
                for new_perm in new_perms:
                    if new_perm["id"] not in existing_perms_model:
                        changed = True
                        break
                    if existing_perms_model[new_perm["id"]] != model.GuildPermissionsData(
                        **new_perm
                    ):
                        changed = True
                        break

            if changed:
                self.logger.debug(f"Detected permissions changes on {scope}, updating them")
                await self.req.update_guild_commands_permissions(scope, new_perms)
            else:
                self.logger.debug(f"No permissions changes detected on {scope}, skipping")

        if delete_from_unused_guilds:
            self.logger.info("Deleting unused guild interactions...")
            other_guilds = [
                guild.id for guild in self._discord.guilds if guild.id not in cmds["guild"]
            ]

            for guild in other_guilds:
                with suppress(Forbidden):
                    existing = await self.req.get_all_commands(guild_id=guild)
                    if len(existing) != 0:
                        self.logger.debug(f"Deleting interactions from {guild}")
                        await self.req.put_interactions(interactions=[], guild_id=guild)

        if delete_perms_from_unused_guilds:
            self.logger.info("Deleting unused guild permissions...")
            other_guilds = [
                guild.id for guild in self._discord.guilds if guild.id not in permissions_map.keys()
            ]
            for guild in other_guilds:
                with suppress(Forbidden):
                    self.logger.debug(f"Deleting permissions from {guild}")
                    existing_perms = await self.req.get_all_guild_commands_permissions(guild)
                    if len(existing_perms) != 0:
                        await self.req.update_guild_commands_permissions(guild, [])

        self.logger.info("Command Interactions has been synced.")

    def add_interaction(
        self,
        cmd,
        name: str = None,
        description: str = None,
        guild_ids: typing.List[int] = None,
        options: list = None,
        default_permission: bool = True,
        permissions: typing.Dict[int, list] = None,
        connector: dict = None,
        has_subcommands: bool = False,
    ):
        """
        Registers command interaction to Interaction.
        .. warning::
            Just using this won't register command interaction to Discord API.
            To register it, check :meth:`.utils.manage_commands.add_interaction` or simply enable `sync_commands`.
        :param cmd: Command Coroutine.
        :type cmd: Coroutine
        :param name: Name of the command interaction. Default name of the coroutine.
        :type name: str
        :param description: Description of the command interaction. Defaults to command docstring or ``None``.
        :type description: str
        :param guild_ids: List of Guild ID of where the command will be used. Default ``None``, which will be global command.
        :type guild_ids: List[int]
        :param options: Options of the command interaction. This will affect ``auto_convert`` and command data at Discord API. Default ``None``.
        :type options: list
        :param default_permission: Sets if users have permission to run command interaction by default, when no permissions are set. Default ``True``.
        :type default_permission: bool
        :param permissions: Dictionary of permissions of the command interaction. Key being target guild_id and value being a list of permissions to apply. Default ``None``.
        :type permissions: dict
        :param connector: Kwargs connector for the command. Default ``None``.
        :type connector: dict
        :param has_subcommands: Whether it has subcommand. Default ``False``.
        :type has_subcommands: bool
        """
        name = name or cmd.__name__
        name = name.lower()
        guild_ids = guild_ids if guild_ids else []
        if not all(isinstance(item, int) for item in guild_ids):
            raise error.IncorrectGuildIDType(
                f"The snowflake IDs {guild_ids} given are not a list of integers. Because of discord.py convention, please use integer IDs instead. Furthermore, the command '{name}' will be deactivated and broken until fixed."
            )
        if name in self.commands:
            tgt = self.commands[name]
            if not tgt.has_subcommands:
                raise error.DuplicateCommand(name)
            has_subcommands = tgt.has_subcommands
            for x in tgt.allowed_guild_ids:
                if x not in guild_ids:
                    guild_ids.append(x)

        description = description or getdoc(cmd)

        if options is None:
            options = manage_commands.generate_options(cmd, description, connector)

        _cmd = {
            "func": cmd,
            "description": description,
            "guild_ids": guild_ids,
            "api_options": options,
            "default_permission": default_permission,
            "api_permissions": permissions,
            "connector": connector or {},
            "has_subcommands": has_subcommands,
        }
        obj = model.BaseCommandObject(name, _cmd)
        self.commands[name] = obj
        self.logger.debug(f"Added command `{name}`")
        return obj

    def _cog_ext_add_context_menu(self, target: int, name: str, guild_ids: list = None):
        """
        Creates a new cog_based context menu command.
        :param cmd: Command Coroutine.
        :type cmd: Coroutine
        :param name: The name of the command
        :type name: str
        :param _type: The context menu type.
        :type _type: int
        """

    def add_context_menu(self, cmd, name: str, _type: int, guild_ids: list = None):
        """
        Creates a new context menu command.
        :param cmd: Command Coroutine.
        :type cmd: Coroutine
        :param name: The name of the command
        :type name: str
        :param _type: The context menu type.
        :type _type: int
        """

        name = [name or cmd.__name__][0]
        guild_ids = guild_ids or []

        if not all(isinstance(item, int) for item in guild_ids):
            raise error.IncorrectGuildIDType(
                f"The snowflake IDs {guild_ids} given are not a list of integers. Because of discord.py convention, please use integer IDs instead. Furthermore, the command '{name}' will be deactivated and broken until fixed."
            )

        if name in self.commands["context"]:
            tgt = self.commands["context"][name]
            if not tgt.has_subcommands:
                raise error.DuplicateCommand(name)
            has_subcommands = tgt.has_subcommands  # noqa
            for x in tgt.allowed_guild_ids:
                if x not in guild_ids:
                    guild_ids.append(x)

        _cmd = {
            "default_permission": None,
            "has_permissions": None,
            "name": name,
            "type": _type,
            "func": cmd,
            "description": "",
            "guild_ids": guild_ids,
            "api_options": [],
            "connector": {},
            "has_subcommands": False,
            "api_permissions": {},
        }

        obj = model.BaseCommandObject(name, cmd=_cmd, _type=_type)
        self.commands["context"][name] = obj
        self.logger.debug(f"Added context command `{name}`")
        return obj

    def add_subcommand(
        self,
        cmd,
        base,
        subcommand_group=None,
        name=None,
        description: str = None,
        base_description: str = None,
        base_default_permission: bool = True,
        base_permissions: typing.Dict[int, list] = None,
        subcommand_group_description: str = None,
        guild_ids: typing.List[int] = None,
        options: list = None,
        connector: dict = None,
    ):
        """
        Registers subcommand to Interaction.
        :param cmd: Subcommand Coroutine.
        :type cmd: Coroutine
        :param base: Name of the base command.
        :type base: str
        :param subcommand_group: Name of the subcommand group, if any. Default ``None`` which represents there is no sub group.
        :type subcommand_group: str
        :param name: Name of the subcommand. Default name of the coroutine.
        :type name: str
        :param description: Description of the subcommand. Defaults to command docstring or ``None``.
        :type description: str
        :param base_description: Description of the base command. Default ``None``.
        :type base_description: str
        :param base_default_permission: Sets if users have permission to run base command by default, when no permissions are set. Default ``True``.
        :type base_default_permission: bool
        :param base_permissions: Dictionary of permissions of the command interaction. Key being target guild_id and value being a list of permissions to apply. Default ``None``.
        :type base_permissions: dict
        :param subcommand_group_description: Description of the subcommand_group. Default ``None``.
        :type subcommand_group_description: str
        :param guild_ids: List of guild ID of where the command will be used. Default ``None``, which will be global command.
        :type guild_ids: List[int]
        :param options: Options of the subcommand. This will affect ``auto_convert`` and command data at Discord API. Default ``None``.
        :type options: list
        :param connector: Kwargs connector for the command. Default ``None``.
        :type connector: dict
        """
        base = base.lower()
        subcommand_group = subcommand_group.lower() if subcommand_group else subcommand_group
        name = name or cmd.__name__
        name = name.lower()
        description = description or getdoc(cmd)
        guild_ids = guild_ids if guild_ids else []
        if not all(isinstance(item, int) for item in guild_ids):
            raise error.IncorrectGuildIDType(
                f"The snowflake IDs {guild_ids} given are not a list of integers. Because of discord.py convention, please use integer IDs instead. Furthermore, the command '{name}' will be deactivated and broken until fixed."
            )

        if base in self.commands:
            for x in guild_ids:
                if x not in self.commands[base].allowed_guild_ids:
                    self.commands[base].allowed_guild_ids.append(x)

        if options is None:
            options = manage_commands.generate_options(cmd, description, connector)

        _cmd = {
            "func": None,
            "description": base_description,
            "guild_ids": guild_ids.copy(),
            "api_options": [],
            "default_permission": base_default_permission,
            "api_permissions": base_permissions,
            "connector": {},
            "has_subcommands": True,
        }
        _sub = {
            "func": cmd,
            "name": name,
            "description": description,
            "base_desc": base_description,
            "sub_group_desc": subcommand_group_description,
            "guild_ids": guild_ids,
            "api_options": options,
            "connector": connector or {},
        }
        if base not in self.commands:
            self.commands[base] = model.BaseCommandObject(base, _cmd)
        else:
            base_command = self.commands[base]
            base_command.has_subcommands = True
            if base_permissions:
                for applicable_guild in base_permissions:
                    if applicable_guild not in base_command.permissions:
                        base_command.permissions[applicable_guild] = []
                    base_command.permissions[applicable_guild].extend(
                        base_permissions[applicable_guild]
                    )
            if base_command.description:
                _cmd["description"] = base_command.description
        if base not in self.subcommands:
            self.subcommands[base] = {}
        if subcommand_group:
            if subcommand_group not in self.subcommands[base]:
                self.subcommands[base][subcommand_group] = {}
            if name in self.subcommands[base][subcommand_group]:
                raise error.DuplicateCommand(f"{base} {subcommand_group} {name}")
            obj = model.SubcommandObject(_sub, base, name, subcommand_group)
            self.subcommands[base][subcommand_group][name] = obj
        else:
            if name in self.subcommands[base]:
                raise error.DuplicateCommand(f"{base} {name}")
            obj = model.SubcommandObject(_sub, base, name)
            self.subcommands[base][name] = obj
        self.logger.debug(
            f"Added subcommand `{base} {subcommand_group or ''} {name or cmd.__name__}`"
        )
        return obj

    def slash(
        self,
        *,
        name: str = None,
        description: str = None,
        guild_ids: typing.List[int] = None,
        options: typing.List[dict] = None,
        default_permission: bool = True,
        permissions: dict = None,
        connector: dict = None,
    ):
        """
        Decorator that registers coroutine as a command interaction.\n
        All decorator args must be passed as keyword-only args.\n
        1 arg for command coroutine is required for ctx(:class:`.model.SlashContext`),
        and if your command interaction has some args, then those args are also required.\n
        All args must be passed as keyword-args.
        .. note::
            If you don't pass `options` but has extra args, then it will automatically generate options.
            However, it is not recommended to use it since descriptions will be "No Description." or the command's description.
        .. warning::
            Unlike discord.py's command, ``*args``, keyword-only args, converters, etc. are not supported or behave differently.
        Example:
        .. code-block:: python
            @slash.slash(name="ping")
            async def _slash(ctx): # Normal usage.
                await ctx.send(content=f"Pong! (`{round(bot.latency*1000)}`ms)")
            @slash.slash(name="pick")
            async def _pick(ctx, choice1, choice2): # Command with 1 or more args.
                await ctx.send(content=str(random.choice([choice1, choice2])))
        To format the connector, follow this example.
        .. code-block:: python
            {
                "example-arg": "example_arg",
                "시간": "hour"
                # Formatting connector is required for
                # using other than english for option parameter name
                # for in case.
            }
        Set discord UI's parameter name as key, and set command coroutine's arg name as value.
        :param name: Name of the command interaction. Default name of the coroutine.
        :type name: str
        :param description: Description of the command interaction. Default ``None``.
        :type description: str
        :param guild_ids: List of Guild ID of where the command will be used. Default ``None``, which will be global command.
        :type guild_ids: List[int]
        :param options: Options of the command interaction. This will affect ``auto_convert`` and command data at Discord API. Default ``None``.
        :type options: List[dict]
        :param default_permission: Sets if users have permission to run command interaction by default, when no permissions are set. Default ``True``.
        :type default_permission: bool
        :param permissions: Permission requirements of the command interaction. Default ``None``.
        :type permissions: dict
        :param connector: Kwargs connector for the command. Default ``None``.
        :type connector: dict
        """
        if not permissions:
            permissions = {}

        def wrapper(cmd):
            decorator_permissions = getattr(cmd, "__permissions__", None)
            if decorator_permissions:
                permissions.update(decorator_permissions)

            obj = self.add_interaction(
                cmd,
                name,
                description,
                guild_ids,
                options,
                default_permission,
                permissions,
                connector,
            )

            return obj

        return wrapper

    def subcommand(
        self,
        *,
        base,
        subcommand_group=None,
        name=None,
        description: str = None,
        base_description: str = None,
        base_desc: str = None,
        base_default_permission: bool = True,
        base_permissions: dict = None,
        subcommand_group_description: str = None,
        sub_group_desc: str = None,
        guild_ids: typing.List[int] = None,
        options: typing.List[dict] = None,
        connector: dict = None,
    ):
        """
        Decorator that registers subcommand.\n
        Unlike discord.py, you don't need base command.\n
        All args must be passed as keyword-args.
        .. note::
            If you don't pass `options` but has extra args, then it will automatically generate options.
            However, it is not recommended to use it since descriptions will be "No Description." or the command's description.
        .. warning::
            Unlike discord.py's command, ``*args``, keyword-only args, converters, etc. are not supported or behave differently.
        Example:
        .. code-block:: python
            # /group say <str>
            @bot.subcommand(base="group", name="say")
            async def _group_say(ctx, _str):
                await ctx.send(content=_str)
            # /group kick user <user>
            @bot.subcommand(base="group",
                              subcommand_group="kick",
                              name="user")
            async def _group_kick_user(ctx, user):
                ...
        :param base: Name of the base command.
        :type base: str
        :param subcommand_group: Name of the subcommand group, if any. Default ``None`` which represents there is no sub group.
        :type subcommand_group: str
        :param name: Name of the subcommand. Default name of the coroutine.
        :type name: str
        :param description: Description of the subcommand. Default ``None``.
        :type description: str
        :param base_description: Description of the base command. Default ``None``.
        :type base_description: str
        :param base_desc: Alias of ``base_description``.
        :param base_default_permission: Sets if users have permission to run command interaction by default, when no permissions are set. Default ``True``.
        :type base_default_permission: bool
        :param permissions: Permission requirements of the command interaction. Default ``None``.
        :type permissions: dict
        :param subcommand_group_description: Description of the subcommand_group. Default ``None``.
        :type subcommand_group_description: str
        :param sub_group_desc: Alias of ``subcommand_group_description``.
        :param guild_ids: List of guild ID of where the command will be used. Default ``None``, which will be global command.
        :type guild_ids: List[int]
        :param options: Options of the subcommand. This will affect ``auto_convert`` and command data at Discord API. Default ``None``.
        :type options: List[dict]
        :param connector: Kwargs connector for the command. Default ``None``.
        :type connector: dict
        """
        base_description = base_description or base_desc
        subcommand_group_description = subcommand_group_description or sub_group_desc
        if not base_permissions:
            base_permissions = {}

        def wrapper(cmd):
            decorator_permissions = getattr(cmd, "__permissions__", None)
            if decorator_permissions:
                base_permissions.update(decorator_permissions)

            obj = self.add_subcommand(
                cmd,
                base,
                subcommand_group,
                name,
                description,
                base_description,
                base_default_permission,
                base_permissions,
                subcommand_group_description,
                guild_ids,
                options,
                connector,
            )

            return obj

        return wrapper

    def permission(self, guild_id: int, permissions: list):
        """
        Decorator that add permissions. This will set the permissions for a single guild, you can use it more than once for each command.
        :param guild_id: ID of the guild for the permissions.
        :type guild_id: int
        :param permissions: List of permissions to be set for the specified guild.
        :type permissions: list
        """

        def wrapper(cmd):
            if not getattr(cmd, "__permissions__", None):
                cmd.__permissions__ = {}
            cmd.__permissions__[guild_id] = permissions
            return cmd

        return wrapper

    def context_menu(self, *, target: int, name: str, guild_ids: list = None):
        """
        Decorator that adds context menu commands.
        :param target: The type of menu.
        :type target: int
        :param name: A name to register as the command in the menu.
        :type name: str
        :param guild_ids: A list of guild IDs to register the command under. Defaults to ``None``.
        :type guild_ids: list
        """

        def wrapper(cmd):

            obj = self.add_context_menu(cmd, name, target, guild_ids)

            return obj

        return wrapper

    def add_component_callback(
        self,
        callback: typing.Coroutine,
        *,
        messages: typing.Union[int, discord.Message, list] = None,
        components: typing.Union[str, dict, list] = None,
        use_callback_name=True,
        component_type: int = None,
    ):
        """
        Adds a coroutine callback to a component.
        Callback can be made to only accept component interactions from a specific messages
        and/or custom_ids of components.
        :param Coroutine callback: The coroutine to be called when the component is interacted with. Must accept a single argument with the type :class:`.context.ComponentContext`.
        :param messages: If specified, only interactions from the message given will be accepted. Can be a message object to check for, or the message ID or list of previous two. Empty list will mean that no interactions are accepted.
        :type messages: Union[discord.Message, int, list]
        :param components: If specified, only interactions with ``custom_id`` of given components will be accepted. Defaults to the name of ``callback`` if ``use_callback_name=True``. Can be a custom ID (str) or component dict (actionrow or button) or list of previous two.
        :type components: Union[str, dict, list]
        :param use_callback_name: Whether the ``custom_id`` defaults to the name of ``callback`` if unspecified. If ``False``, either ``messages`` or ``components`` must be specified.
        :type use_callback_name: bool
        :param component_type: The type of the component to avoid collisions with other component types. See :class:`.model.ComponentType`.
        :type component_type: Optional[int]
        :raises: .error.DuplicateCustomID, .error.IncorrectFormat
        """

        message_ids = list(get_messages_ids(messages)) if messages is not None else [None]
        custom_ids = list(get_components_ids(components)) if components is not None else [None]

        if use_callback_name and custom_ids == [None]:
            custom_ids = [callback.__name__]

        if message_ids == [None] and custom_ids == [None]:
            raise error.IncorrectFormat("You must specify messages or components (or both)")

        callback_obj = model.ComponentCallbackObject(
            callback, message_ids, custom_ids, component_type
        )
        self._add_comp_callback_obj(callback_obj)
        return callback_obj

    def _add_comp_callback_obj(self, callback_obj):
        component_type = callback_obj.component_type

        for message_id, custom_id in callback_obj.keys:
            self._register_comp_callback_obj(callback_obj, message_id, custom_id, component_type)

    def _register_comp_callback_obj(self, callback_obj, message_id, custom_id, component_type):
        message_id_dict = self.components
        custom_id_dict = message_id_dict.setdefault(message_id, {})
        component_type_dict = custom_id_dict.setdefault(custom_id, {})

        if component_type in component_type_dict:
            raise error.DuplicateCallback(message_id, custom_id, component_type)

        component_type_dict[component_type] = callback_obj
        self.logger.debug(
            f"Added component callback for "
            f"message ID {message_id or '<any>'}, "
            f"custom_id `{custom_id or '<any>'}`, "
            f"component_type `{component_type or '<any>'}`"
        )

    def extend_component_callback(
        self,
        callback_obj: model.ComponentCallbackObject,
        message_id: int = None,
        custom_id: str = None,
    ):
        """
        Registers existing callback object (:class:`.model.ComponentCallbackObject`)
        for specific combination of message_id, custom_id, component_type.
        :param callback_obj: callback object.
        :type callback_obj: model.ComponentCallbackObject
        :param message_id: If specified, only removes the callback for the specific message ID.
        :type message_id: Optional[.model]
        :param custom_id: The ``custom_id`` of the component.
        :type custom_id: Optional[str]
        :raises: .error.DuplicateCustomID, .error.IncorrectFormat
        """

        component_type = callback_obj.component_type
        self._register_comp_callback_obj(callback_obj, message_id, custom_id, component_type)
        callback_obj.keys.add((message_id, custom_id))

    def get_component_callback(
        self,
        message_id: int = None,
        custom_id: str = None,
        component_type: int = None,
    ):
        """
        Returns component callback (or None if not found) for specific combination of message_id, custom_id, component_type.
        :param message_id: If specified, only removes the callback for the specific message ID.
        :type message_id: Optional[.model]
        :param custom_id: The ``custom_id`` of the component.
        :type custom_id: Optional[str]
        :param component_type: The type of the component. See :class:`.model.ComponentType`.
        :type component_type: Optional[int]
        :return: Optional[model.ComponentCallbackObject]
        """
        message_id_dict = self.components
        try:
            custom_id_dict = _get_val(message_id_dict, message_id)
            component_type_dict = _get_val(custom_id_dict, custom_id)
            callback = _get_val(component_type_dict, component_type)

        except KeyError:
            pass
        else:
            return callback

    def remove_component_callback(
        self, message_id: int = None, custom_id: str = None, component_type: int = None
    ):
        """
        Removes a component callback from specific combination of message_id, custom_id, component_type.
        :param message_id: If specified, only removes the callback for the specific message ID.
        :type message_id: Optional[int]
        :param custom_id: The ``custom_id`` of the component.
        :type custom_id: Optional[str]
        :param component_type: The type of the component. See :class:`.model.ComponentType`.
        :type component_type: Optional[int]
        :raises: .error.IncorrectFormat
        """
        try:
            callback = self.components[message_id][custom_id].pop(component_type)
            if not self.components[message_id][custom_id]:
                self.components[message_id].pop(custom_id)
                if not self.components[message_id]:
                    self.components.pop(message_id)
        except KeyError:
            raise error.IncorrectFormat(
                f"Callback for "
                f"message ID `{message_id or '<any>'}`, "
                f"custom_id `{custom_id or '<any>'}`, "
                f"component_type `{component_type or '<any>'}` is not registered!"
            )
        else:
            callback.keys.remove((message_id, custom_id))

    def remove_component_callback_obj(self, callback_obj: model.ComponentCallbackObject):
        """
        Removes a component callback from all related message_id, custom_id listeners.
        :param callback_obj: callback object.
        :type callback_obj: model.ComponentCallbackObject
        :raises: .error.IncorrectFormat
        """
        if not callback_obj.keys:
            raise error.IncorrectFormat("Callback already removed from any listeners")

        component_type = callback_obj.component_type
        for message_id, custom_id in callback_obj.keys.copy():
            self.remove_component_callback(message_id, custom_id, component_type)

    def component_callback(
        self,
        *,
        messages: typing.Union[int, discord.Message, list] = None,
        components: typing.Union[str, dict, list] = None,
        use_callback_name=True,
        component_type: int = None,
    ):
        """
        Decorator that registers a coroutine as a component callback.
        Adds a coroutine callback to a component.
        Callback can be made to only accept component interactions from a specific messages
        and/or custom_ids of components.
        :param messages: If specified, only interactions from the message given will be accepted. Can be a message object to check for, or the message ID or list of previous two. Empty list will mean that no interactions are accepted.
        :type messages: Union[discord.Message, int, list]
        :param components: If specified, only interactions with ``custom_id`` of given components will be accepted. Defaults to the name of ``callback`` if ``use_callback_name=True``. Can be a custom ID (str) or component dict (actionrow or button) or list of previous two.
        :type components: Union[str, dict, list]
        :param use_callback_name: Whether the ``custom_id`` defaults to the name of ``callback`` if unspecified. If ``False``, either ``messages`` or ``components`` must be specified.
        :type use_callback_name: bool
        :param component_type: The type of the component to avoid collisions with other component types. See :class:`.model.ComponentType`.
        :type component_type: Optional[int]
        :raises: .error.DuplicateCustomID, .error.IncorrectFormat
        """

        def wrapper(callback):
            return self.add_component_callback(
                callback,
                messages=messages,
                components=components,
                use_callback_name=use_callback_name,
                component_type=component_type,
            )

        return wrapper

    async def process_options(
        self,
        guild: Guild,
        options: list,
        connector: dict,
        temporary_auto_convert: dict = None,
    ) -> dict:
        """
        Processes Role, User, and Channel option types to discord.py's models.
        :param guild: Guild of the command message.
        :type guild: discord.Guild
        :param options: Dict of options.
        :type options: list
        :param connector: Kwarg connector.
        :param temporary_auto_convert: Temporary parameter, use this if options doesn't have ``type`` keyword.
        :return: Union[list, dict]
        """

        if not guild or not isinstance(guild, Guild):
            return {connector.get(x["name"]) or x["name"]: x["value"] for x in options}

        converters = [
            [guild.get_member, guild.fetch_member],
            guild.get_channel,
            guild.get_role,
        ]

        types = {
            "user": 0,
            "USER": 0,
            model.InteractionOptionType.USER: 0,
            "6": 0,
            6: 0,
            "channel": 1,
            "CHANNEL": 1,
            model.InteractionOptionType.CHANNEL: 1,
            "7": 1,
            7: 1,
            "role": 2,
            "ROLE": 2,
            model.InteractionOptionType.ROLE: 2,
            8: 2,
            "8": 2,
        }

        to_return = {}

        for x in options:
            processed = None  # This isn't the best way, but we should to reduce duplicate lines.

            # This is to temporarily fix Issue #97, that on Android device
            # does not give option type from API.
            if "type" not in x:
                x["type"] = temporary_auto_convert[x["name"]]

            if x["type"] not in types:
                processed = x["value"]
            else:
                loaded_converter = converters[types[x["type"]]]
                if isinstance(loaded_converter, list):  # For user type.
                    cache_first = loaded_converter[0](int(x["value"]))
                    if cache_first:
                        processed = cache_first
                    else:
                        loaded_converter = loaded_converter[1]
                if not processed:
                    try:
                        processed = (
                            await loaded_converter(int(x["value"]))
                            if iscoroutinefunction(loaded_converter)
                            else loaded_converter(int(x["value"]))
                        )
                    except (
                        Forbidden,
                        HTTPException,
                        NotFound,
                    ):  # Just in case.
                        self.logger.warning("Failed fetching discord object! Passing ID instead.")
                        processed = int(x["value"])
            to_return[connector.get(x["name"]) or x["name"]] = processed
        return to_return

    async def invoke_command(self, func, ctx, args):
        """
        Invokes command.
        :param func: Command coroutine.
        :param ctx: Context.
        :param args: Args. Can be list or dict.
        """
        try:
            if isinstance(args, dict):
                ctx.kwargs = args
                ctx.args = list(args.values())
            await func.invoke(ctx, **args)
        except Exception as ex:
            if not await self._handle_invoke_error(func, ctx, ex):
                await self.on_interaction_error(ctx, ex)

    async def invoke_component_callback(self, func, ctx):
        """
        Invokes component callback.
        :param func: Component callback object.
        :param ctx: Context.
        """
        try:
            await func.invoke(ctx)
        except Exception as ex:
            if not await self._handle_invoke_error(func, ctx, ex):
                await self.on_component_callback_error(ctx, ex)

    async def _handle_invoke_error(self, func, ctx, ex):
        if hasattr(func, "on_error"):
            if func.on_error is not None:
                try:
                    if hasattr(func, "cog"):
                        await func.on_error(func.cog, ctx, ex)
                    else:
                        await func.on_error(ctx, ex)
                    return True
                except Exception as e:
                    self.logger.error(f"{ctx.command}:: Error using error decorator: {e}")
        return False

    async def on_socket_response(self, msg):
        """
        This event listener is automatically registered at initialization of this class.
        .. warning::
            DO NOT MANUALLY REGISTER, OVERRIDE, OR WHATEVER ACTION TO THIS COROUTINE UNLESS YOU KNOW WHAT YOU ARE DOING.
        :param msg: Gateway message.
        """
        if msg["t"] != "INTERACTION_CREATE":
            return

        to_use = msg["d"]
        interaction_type = to_use["type"]

        if interaction_type in (1, 2):
            await self._on_slash(to_use)
            await self._on_context_menu(to_use)
        elif interaction_type == 3:
            try:
                await self._on_component(to_use)
            except KeyError:
                pass
            finally:
                await self._on_context_menu(to_use)
        else:
            raise NotImplementedError(
                f"Unknown Interaction Received: {interaction_type}"
            )
        return

    async def _on_component(self, to_use):
        ctx = context.ComponentContext(self.req, to_use, self._discord, self.logger)
        self._discord.dispatch("component", ctx)

        callback = self.get_component_callback(
            ctx.origin_message_id, ctx.custom_id, ctx.component_type
        )
        if callback is not None:
            self._discord.dispatch("component_callback", ctx, callback)
            await self.invoke_component_callback(callback, ctx)

    async def _on_slash(self, to_use):
        if to_use["data"]["name"] in self.commands:

            ctx = context.SlashContext(self.req, to_use, self._discord, self.logger)
            cmd_name = to_use["data"]["name"]

            if cmd_name not in self.commands and cmd_name in self.subcommands:
                return await self.handle_subcommand(ctx, to_use)

            selected_cmd = self.commands[to_use["data"]["name"]]

            if type(selected_cmd) == dict:
                return

            if selected_cmd._type != 1:
                return

            if (
                selected_cmd.allowed_guild_ids
                and ctx.guild_id not in selected_cmd.allowed_guild_ids
            ):
                return

            if selected_cmd.has_subcommands and not selected_cmd.func:
                return await self.handle_subcommand(ctx, to_use)

            if "options" in to_use["data"]:
                for x in to_use["data"]["options"]:
                    if "value" not in x:
                        return await self.handle_subcommand(ctx, to_use)
            temporary_auto_convert = {}
            for x in selected_cmd.options:
                temporary_auto_convert[x["name"].lower()] = x["type"]

            args = (
                await self.process_options(
                    ctx.guild,
                    to_use["data"]["options"],
                    selected_cmd.connector,
                    temporary_auto_convert,
                )
                if "options" in to_use["data"]
                else {}
            )

            self._discord.dispatch("interaction", ctx)

            await self.invoke_command(selected_cmd, ctx, args)

    async def _on_context_menu(self, to_use):
        if "name" not in to_use["data"].keys():
            return

        if to_use["data"]["name"] in self.commands["context"]:
            ctx = context.MenuContext(self.req, to_use, self._discord, self.logger)
            cmd_name = to_use["data"]["name"]

            if cmd_name not in self.commands["context"] and cmd_name in self.subcommands:
                return

            selected_cmd = self.commands["context"][cmd_name]

            if (
                selected_cmd.allowed_guild_ids
                and ctx.guild_id not in selected_cmd.allowed_guild_ids
            ):
                return

            if selected_cmd.has_subcommands and not selected_cmd.func:
                return await self.handle_subcommand(ctx, to_use)

            if "options" in to_use["data"]:
                for x in to_use["data"]["options"]:
                    if "value" not in x:
                        return await self.handle_subcommand(ctx, to_use)

            self._discord.dispatch("context_menu", ctx)

            await self.invoke_command(selected_cmd, ctx, args={})


        elif to_use["data"]["name"] in self.commands:
            ctx = context.MenuContext(self.req, to_use, self._discord, self.logger)
            cmd_name = to_use["data"]["name"]

            if cmd_name not in self.commands and cmd_name in self.subcommands:
                return

            selected_cmd = self.commands[cmd_name]
            if type(selected_cmd) == dict:
                return
            if selected_cmd._type == 1: 
                return

            if (
                selected_cmd.allowed_guild_ids
                and ctx.guild_id not in selected_cmd.allowed_guild_ids
            ):
                return

            if selected_cmd.has_subcommands and not selected_cmd.func:
                return await self.handle_subcommand(ctx, to_use)

            if "options" in to_use["data"]:
                for x in to_use["data"]["options"]:
                    if "value" not in x:
                        return await self.handle_subcommand(ctx, to_use)

            self._discord.dispatch("context_menu", ctx)

            await self.invoke_command(selected_cmd, ctx, args={})

    async def handle_subcommand(self, ctx: context.SlashContext, data: dict):
        """
        Coroutine for handling subcommand.
        .. warning::
            Do not manually call this.
        :param ctx: :class:`.model.SlashContext` instance.
        :param data: Gateway message.
        """
        if data["data"]["name"] not in self.subcommands:
            return
        base = self.subcommands[data["data"]["name"]]
        sub = data["data"]["options"][0]
        sub_name = sub["name"]
        if sub_name not in base:
            return
        ctx.subcommand_name = sub_name
        sub_opts = sub["options"] if "options" in sub else []
        for x in sub_opts:
            if "options" in x or "value" not in x:
                sub_group = x["name"]
                if sub_group not in base[sub_name]:
                    return
                ctx.subcommand_group = sub_group
                selected = base[sub_name][sub_group]

                temporary_auto_convert = {}
                for n in selected.options:
                    temporary_auto_convert[n["name"].lower()] = n["type"]

                args = (
                    await self.process_options(
                        ctx.guild, x["options"], selected.connector, temporary_auto_convert
                    )
                    if "options" in x
                    else {}
                )
                self._discord.dispatch("interaction", ctx)
                await self.invoke_command(selected, ctx, args)
                return
        selected = base[sub_name]

        temporary_auto_convert = {}
        for n in selected.options:
            temporary_auto_convert[n["name"].lower()] = n["type"]

        args = (
            await self.process_options(
                ctx.guild, sub_opts, selected.connector, temporary_auto_convert
            )
            if "options" in sub
            else {}
        )
        self._discord.dispatch("interaction", ctx)
        await self.invoke_command(selected, ctx, args)

    def _on_error(self, ctx, ex, event_name):
        on_event = "on_" + event_name
        if self.has_listener:
            if self._discord.extra_events.get(on_event):
                self._discord.dispatch(event_name, ctx, ex)
                return True
        if hasattr(self._discord, on_event):
            self._discord.dispatch(event_name, ctx, ex)
            return True
        return False

    async def on_interaction_error(self, ctx, ex):
        """
        Handles Exception occurred from invoking command.
        Example of adding event:
        .. code-block:: python
            @client.event
            async def on_interaction_error(ctx, ex):
                ...
        Example of adding listener:
        .. code-block:: python
            @bot.listen()
            async def on_interaction_error(ctx, ex):
                ...
        :param ctx: Context of the command.
        :type ctx: :class:`.model.SlashContext`
        :param ex: Exception from the command invoke.
        :type ex: Exception
        :return:
        """
        if not self._on_error(ctx, ex, "interaction_error"):
            self.logger.exception(
                f"An exception has occurred while executing command `{ctx.name}`:"
            )

    async def on_component_callback_error(self, ctx, ex):
        """
        Handles Exception occurred from invoking component callback.
        Example of adding event:
        .. code-block:: python
            @client.event
            async def on_component_callback_error(ctx, ex):
                ...
        Example of adding listener:
        .. code-block:: python
            @bot.listen()
            async def on_component_callback_error(ctx, ex):
                ...
        :param ctx: Context of the callback.
        :type ctx: :class:`.model.ComponentContext`
        :param ex: Exception from the command invoke.
        :type ex: Exception
        :return:
        """
        if not self._on_error(ctx, ex, "component_callback_error"):
            # Prints exception if not overridden or has no listener for error.
            self.logger.exception(
                f"An exception has occurred while executing component callback custom ID `{ctx.custom_id}`:"
            )

class Client:
    r"""Represents a client connection that connects to Discord.
    This class is used to interact with the Discord WebSocket and API.

    A number of options can be passed to the :class:`Client`.

    Parameters
    -----------
    max_messages: Optional[:class:`int`]
        The maximum number of messages to store in the internal message cache.
        This defaults to ``1000``. Passing in ``None`` disables the message cache.

        .. versionchanged:: 1.3
            Allow disabling the message cache and change the default size to ``1000``.
    loop: Optional[:class:`asyncio.AbstractEventLoop`]
        The :class:`asyncio.AbstractEventLoop` to use for asynchronous operations.
        Defaults to ``None``, in which case the default event loop is used via
        :func:`asyncio.get_event_loop()`.
    connector: Optional[:class:`aiohttp.BaseConnector`]
        The connector to use for connection pooling.
    proxy: Optional[:class:`str`]
        Proxy URL.
    proxy_auth: Optional[:class:`aiohttp.BasicAuth`]
        An object that represents proxy HTTP Basic Authorization.
    shard_id: Optional[:class:`int`]
        Integer starting at ``0`` and less than :attr:`.shard_count`.
    shard_count: Optional[:class:`int`]
        The total number of shards.
    application_id: :class:`int`
        The client's application ID.
    intents: :class:`Intents`
        The intents that you want to enable for the session. This is a way of
        disabling and enabling certain gateway events from triggering and being sent.
        If not given, defaults to a regularly constructed :class:`Intents` class.

        .. versionadded:: 1.5
    member_cache_flags: :class:`MemberCacheFlags`
        Allows for finer control over how the library caches members.
        If not given, defaults to cache as much as possible with the
        currently selected intents.

        .. versionadded:: 1.5
    chunk_guilds_at_startup: :class:`bool`
        Indicates if :func:`.on_ready` should be delayed to chunk all guilds
        at start-up if necessary. This operation is incredibly slow for large
        amounts of guilds. The default is ``True`` if :attr:`Intents.members`
        is ``True``.

        .. versionadded:: 1.5
    status: Optional[:class:`.Status`]
        A status to start your presence with upon logging on to Discord.
    activity: Optional[:class:`.BaseActivity`]
        An activity to start your presence with upon logging on to Discord.
    allowed_mentions: Optional[:class:`AllowedMentions`]
        Control how the client handles mentions by default on every message sent.

        .. versionadded:: 1.4
    heartbeat_timeout: :class:`float`
        The maximum numbers of seconds before timing out and restarting the
        WebSocket in the case of not receiving a HEARTBEAT_ACK. Useful if
        processing the initial packets take too long to the point of disconnecting
        you. The default timeout is 60 seconds.
    guild_ready_timeout: :class:`float`
        The maximum number of seconds to wait for the GUILD_CREATE stream to end before
        preparing the member cache and firing READY. The default timeout is 2 seconds.

        .. versionadded:: 1.4
    assume_unsync_clock: :class:`bool`
        Whether to assume the system clock is unsynced. This applies to the ratelimit handling
        code. If this is set to ``True``, the default, then the library uses the time to reset
        a rate limit bucket given by Discord. If this is ``False`` then your system clock is
        used to calculate how long to sleep for. If this is set to ``False`` it is recommended to
        sync your system clock to Google's NTP server.

        .. versionadded:: 1.3
    enable_debug_events: :class:`bool`
        Whether to enable events that are useful only for debugging gateway related information.

        Right now this involves :func:`on_socket_raw_receive` and :func:`on_socket_raw_send`. If
        this is ``False`` then those events will not be dispatched (due to performance considerations).
        To enable these events, this must be set to ``True``. Defaults to ``False``.

        .. versionadded:: 2.0

    Attributes
    -----------
    ws
        The websocket gateway the client is currently connected to. Could be ``None``.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop that the client uses for asynchronous operations.
    """
    def __init__(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **options: Any,
    ):
        # self.ws is set in the connect method
        self.ws: DiscordWebSocket = None  # type: ignore
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        self._listeners: Dict[str, List[Tuple[asyncio.Future, Callable[..., bool]]]] = {}
        self.shard_id: Optional[int] = options.get('shard_id')
        self.shard_count: Optional[int] = options.get('shard_count')

        connector: Optional[aiohttp.BaseConnector] = options.pop('connector', None)
        proxy: Optional[str] = options.pop('proxy', None)
        proxy_auth: Optional[aiohttp.BasicAuth] = options.pop('proxy_auth', None)
        unsync_clock: bool = options.pop('assume_unsync_clock', True)
        self.http: HTTPClient = HTTPClient(connector, proxy=proxy, proxy_auth=proxy_auth, unsync_clock=unsync_clock, loop=self.loop)

        self._handlers: Dict[str, Callable] = {
            'ready': self._handle_ready
        }

        self._hooks: Dict[str, Callable] = {
            'before_identify': self._call_before_identify_hook
        }

        self._enable_debug_events: bool = options.pop('enable_debug_events', False)
        self._connection: ConnectionState = self._get_state(**options)
        self._connection.shard_count = self.shard_count
        self._closed: bool = False
        self._ready: asyncio.Event = asyncio.Event()
        self._connection._get_websocket = self._get_websocket
        self._connection._get_client = lambda: self

        if VoiceClient.warn_nacl:
            VoiceClient.warn_nacl = False
            _log.warning("PyNaCl is not installed, voice will NOT be supported")

    # internals

    def _get_websocket(self, guild_id: Optional[int] = None, *, shard_id: Optional[int] = None) -> DiscordWebSocket:
        return self.ws

    def _get_state(self, **options: Any) -> ConnectionState:
        return ConnectionState(dispatch=self.dispatch, handlers=self._handlers,
                               hooks=self._hooks, http=self.http, loop=self.loop, **options)

    def _handle_ready(self) -> None:
        self._ready.set()

    @property
    def latency(self) -> float:
        """:class:`float`: Measures latency between a HEARTBEAT and a HEARTBEAT_ACK in seconds.

        This could be referred to as the Discord WebSocket protocol latency.
        """
        ws = self.ws
        return float('nan') if not ws else ws.latency

    def is_ws_ratelimited(self) -> bool:
        """:class:`bool`: Whether the websocket is currently rate limited.

        This can be useful to know when deciding whether you should query members
        using HTTP or via the gateway.

        .. versionadded:: 1.6
        """
        if self.ws:
            return self.ws.is_ratelimited()
        return False

    @property
    def user(self) -> Optional[ClientUser]:
        """Optional[:class:`.ClientUser`]: Represents the connected client. ``None`` if not logged in."""
        return self._connection.user

    @property
    def guilds(self) -> List[Guild]:
        """List[:class:`.Guild`]: The guilds that the connected client is a member of."""
        return self._connection.guilds

    @property
    def emojis(self) -> List[Emoji]:
        """List[:class:`.Emoji`]: The emojis that the connected client has."""
        return self._connection.emojis

    @property
    def stickers(self) -> List[GuildSticker]:
        """List[:class:`.GuildSticker`]: The stickers that the connected client has.

        .. versionadded:: 2.0
        """
        return self._connection.stickers

    @property
    def cached_messages(self) -> Sequence[Message]:
        """Sequence[:class:`.Message`]: Read-only list of messages the connected client has cached.

        .. versionadded:: 1.1
        """
        return utils.SequenceProxy(self._connection._messages or [])

    @property
    def private_channels(self) -> List[PrivateChannel]:
        """List[:class:`.abc.PrivateChannel`]: The private channels that the connected client is participating on.

        .. note::

            This returns only up to 128 most recent private channels due to an internal working
            on how Discord deals with private channels.
        """
        return self._connection.private_channels

    @property
    def voice_clients(self) -> List[VoiceProtocol]:
        """List[:class:`.VoiceProtocol`]: Represents a list of voice connections.

        These are usually :class:`.VoiceClient` instances.
        """
        return self._connection.voice_clients

    @property
    def application_id(self) -> Optional[int]:
        """Optional[:class:`int`]: The client's application ID.

        If this is not passed via ``__init__`` then this is retrieved
        through the gateway when an event contains the data. Usually
        after :func:`~discord.on_connect` is called.
        
        .. versionadded:: 2.0
        """
        return self._connection.application_id

    @property
    def application_flags(self) -> ApplicationFlags:
        """:class:`~discord.ApplicationFlags`: The client's application flags.

        .. versionadded:: 2.0
        """
        return self._connection.application_flags  # type: ignore

    def is_ready(self) -> bool:
        """:class:`bool`: Specifies if the client's internal cache is ready for use."""
        return self._ready.is_set()

    async def _run_event(self, coro: Callable[..., Coroutine[Any, Any, Any]], event_name: str, *args: Any, **kwargs: Any) -> None:
        try:
            await coro(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.on_error(event_name, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    def _schedule_event(self, coro: Callable[..., Coroutine[Any, Any, Any]], event_name: str, *args: Any, **kwargs: Any) -> asyncio.Task:
        wrapped = self._run_event(coro, event_name, *args, **kwargs)
        # Schedules the task
        return asyncio.create_task(wrapped, name=f'discord.py: {event_name}')

    def dispatch(self, event: str, *args: Any, **kwargs: Any) -> None:
        _log.debug('Dispatching event %s', event)
        method = 'on_' + event

        listeners = self._listeners.get(event)
        if listeners:
            removed = []
            for i, (future, condition) in enumerate(listeners):
                if future.cancelled():
                    removed.append(i)
                    continue

                try:
                    result = condition(*args)
                except Exception as exc:
                    future.set_exception(exc)
                    removed.append(i)
                else:
                    if result:
                        if len(args) == 0:
                            future.set_result(None)
                        elif len(args) == 1:
                            future.set_result(args[0])
                        else:
                            future.set_result(args)
                        removed.append(i)

            if len(removed) == len(listeners):
                self._listeners.pop(event)
            else:
                for idx in reversed(removed):
                    del listeners[idx]

        try:
            coro = getattr(self, method)
        except AttributeError:
            pass
        else:
            self._schedule_event(coro, method, *args, **kwargs)

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        """|coro|

        The default error handler provided by the client.

        By default this prints to :data:`sys.stderr` however it could be
        overridden to have a different implementation.
        Check :func:`~discord.on_error` for more details.
        """
        print(f'Ignoring exception in {event_method}', file=sys.stderr)
        traceback.print_exc()

    # hooks

    async def _call_before_identify_hook(self, shard_id: Optional[int], *, initial: bool = False) -> None:
        # This hook is an internal hook that actually calls the public one.
        # It allows the library to have its own hook without stepping on the
        # toes of those who need to override their own hook.
        await self.before_identify_hook(shard_id, initial=initial)

    async def before_identify_hook(self, shard_id: Optional[int], *, initial: bool = False) -> None:
        """|coro|

        A hook that is called before IDENTIFYing a session. This is useful
        if you wish to have more control over the synchronization of multiple
        IDENTIFYing clients.

        The default implementation sleeps for 5 seconds.

        .. versionadded:: 1.4

        Parameters
        ------------
        shard_id: :class:`int`
            The shard ID that requested being IDENTIFY'd
        initial: :class:`bool`
            Whether this IDENTIFY is the first initial IDENTIFY.
        """

        if not initial:
            await asyncio.sleep(5.0)

    # login state management

    async def login(self, token: str) -> None:
        """|coro|

        Logs in the client with the specified credentials.


        Parameters
        -----------
        token: :class:`str`
            The authentication token. Do not prefix this token with
            anything as the library will do it for you.

        Raises
        ------
        :exc:`.LoginFailure`
            The wrong credentials are passed.
        :exc:`.HTTPException`
            An unknown HTTP related error occurred,
            usually when it isn't 200 or the known incorrect credentials
            passing status code.
        """

        _log.info('logging in using static token')

        data = await self.http.static_login(token.strip())
        self._connection.user = ClientUser(state=self._connection, data=data)

    async def connect(self, *, reconnect: bool = True) -> None:
        """|coro|

        Creates a websocket connection and lets the websocket listen
        to messages from Discord. This is a loop that runs the entire
        event system and miscellaneous aspects of the library. Control
        is not resumed until the WebSocket connection is terminated.

        Parameters
        -----------
        reconnect: :class:`bool`
            If we should attempt reconnecting, either due to internet
            failure or a specific failure on Discord's part. Certain
            disconnects that lead to bad state will not be handled (such as
            invalid sharding payloads or bad tokens).

        Raises
        -------
        :exc:`.GatewayNotFound`
            If the gateway to connect to Discord is not found. Usually if this
            is thrown then there is a Discord API outage.
        :exc:`.ConnectionClosed`
            The websocket connection has been terminated.
        """

        backoff = ExponentialBackoff()
        ws_params = {
            'initial': True,
            'shard_id': self.shard_id,
        }
        while not self.is_closed():
            try:
                coro = DiscordWebSocket.from_client(self, **ws_params)
                self.ws = await asyncio.wait_for(coro, timeout=60.0)
                ws_params['initial'] = False
                while True:
                    await self.ws.poll_event()
            except ReconnectWebSocket as e:
                _log.info('Got a request to %s the websocket.', e.op)
                self.dispatch('disconnect')
                ws_params.update(sequence=self.ws.sequence, resume=e.resume, session=self.ws.session_id)
                continue
            except (OSError,
                    HTTPException,
                    GatewayNotFound,
                    ConnectionClosed,
                    aiohttp.ClientError,
                    asyncio.TimeoutError) as exc:

                self.dispatch('disconnect')
                if not reconnect:
                    await self.close()
                    if isinstance(exc, ConnectionClosed) and exc.code == 1000:
                        # clean close, don't re-raise this
                        return
                    raise

                if self.is_closed():
                    return

                # If we get connection reset by peer then try to RESUME
                if isinstance(exc, OSError) and exc.errno in (54, 10054):
                    ws_params.update(sequence=self.ws.sequence, initial=False, resume=True, session=self.ws.session_id)
                    continue

                # We should only get this when an unhandled close code happens,
                # such as a clean disconnect (1000) or a bad state (bad token, no sharding, etc)
                # sometimes, discord sends us 1000 for unknown reasons so we should reconnect
                # regardless and rely on is_closed instead
                if isinstance(exc, ConnectionClosed):
                    if exc.code == 4014:
                        raise PrivilegedIntentsRequired(exc.shard_id) from None
                    if exc.code != 1000:
                        await self.close()
                        raise

                retry = backoff.delay()
                _log.exception("Attempting a reconnect in %.2fs", retry)
                await asyncio.sleep(retry)
                # Always try to RESUME the connection
                # If the connection is not RESUME-able then the gateway will invalidate the session.
                # This is apparently what the official Discord client does.
                ws_params.update(sequence=self.ws.sequence, resume=True, session=self.ws.session_id)

    async def close(self) -> None:
        """|coro|

        Closes the connection to Discord.
        """
        if self._closed:
            return

        self._closed = True

        for voice in self.voice_clients:
            try:
                await voice.disconnect(force=True)
            except Exception:
                # if an error happens during disconnects, disregard it.
                pass

        if self.ws is not None and self.ws.open:
            await self.ws.close(code=1000)

        await self.http.close()
        self._ready.clear()

    def clear(self) -> None:
        """Clears the internal state of the bot.

        After this, the bot can be considered "re-opened", i.e. :meth:`is_closed`
        and :meth:`is_ready` both return ``False`` along with the bot's internal
        cache cleared.
        """
        self._closed = False
        self._ready.clear()
        self._connection.clear()
        self.http.recreate()

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        """|coro|

        A shorthand coroutine for :meth:`login` + :meth:`connect`.

        Raises
        -------
        TypeError
            An unexpected keyword argument was received.
        """
        await self.login(token)
        await self.connect(reconnect=reconnect)

    def run(self, *args: Any, **kwargs: Any) -> None:
        """A blocking call that abstracts away the event loop
        initialisation from you.

        If you want more control over the event loop then this
        function should not be used. Use :meth:`start` coroutine
        or :meth:`connect` + :meth:`login`.

        Roughly Equivalent to: ::

            try:
                loop.run_until_complete(start(*args, **kwargs))
            except KeyboardInterrupt:
                loop.run_until_complete(close())
                # cancel all tasks lingering
            finally:
                loop.close()

        .. warning::

            This function must be the last function to call due to the fact that it
            is blocking. That means that registration of events or anything being
            called after this function call will not execute until it returns.
        """
        loop = self.loop

        try:
            loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
            loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
        except NotImplementedError:
            pass

        async def runner():
            try:
                await self.start(*args, **kwargs)
            finally:
                if not self.is_closed():
                    await self.close()

        def stop_loop_on_completion(f):
            loop.stop()

        future = asyncio.ensure_future(runner(), loop=loop)
        future.add_done_callback(stop_loop_on_completion)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            _log.info('Received signal to terminate bot and event loop.')
        finally:
            future.remove_done_callback(stop_loop_on_completion)
            _log.info('Cleaning up tasks.')
            _cleanup_loop(loop)

        if not future.cancelled():
            try:
                return future.result()
            except KeyboardInterrupt:
                # I am unsure why this gets raised here but suppress it anyway
                return None

    # properties

    def is_closed(self) -> bool:
        """:class:`bool`: Indicates if the websocket connection is closed."""
        return self._closed

    @property
    def activity(self) -> Optional[ActivityTypes]:
        """Optional[:class:`.BaseActivity`]: The activity being used upon
        logging in.
        """
        return create_activity(self._connection._activity)

    @activity.setter
    def activity(self, value: Optional[ActivityTypes]) -> None:
        if value is None:
            self._connection._activity = None
        elif isinstance(value, BaseActivity):
            # ConnectionState._activity is typehinted as ActivityPayload, we're passing Dict[str, Any]
            self._connection._activity = value.to_dict() # type: ignore
        else:
            raise TypeError('activity must derive from BaseActivity.')
    
    @property
    def status(self):
        """:class:`.Status`:
        The status being used upon logging on to Discord.

        .. versionadded: 2.0
        """
        if self._connection._status in set(state.value for state in Status):
            return Status(self._connection._status)
        return Status.online

    @status.setter
    def status(self, value):
        if value is Status.offline:
            self._connection._status = 'invisible'
        elif isinstance(value, Status):
            self._connection._status = str(value)
        else:
            raise TypeError('status must derive from Status.')

    @property
    def allowed_mentions(self) -> Optional[AllowedMentions]:
        """Optional[:class:`~discord.AllowedMentions`]: The allowed mention configuration.

        .. versionadded:: 1.4
        """
        return self._connection.allowed_mentions

    @allowed_mentions.setter
    def allowed_mentions(self, value: Optional[AllowedMentions]) -> None:
        if value is None or isinstance(value, AllowedMentions):
            self._connection.allowed_mentions = value
        else:
            raise TypeError(f'allowed_mentions must be AllowedMentions not {value.__class__!r}')

    @property
    def intents(self) -> Intents:
        """:class:`~discord.Intents`: The intents configured for this connection.

        .. versionadded:: 1.5
        """
        return self._connection.intents

    # helpers/getters

    @property
    def users(self) -> List[User]:
        """List[:class:`~discord.User`]: Returns a list of all the users the bot can see."""
        return list(self._connection._users.values())

    def get_channel(self, id: int, /) -> Optional[Union[GuildChannel, Thread, PrivateChannel]]:
        """Returns a channel or thread with the given ID.

        Parameters
        -----------
        id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[Union[:class:`.abc.GuildChannel`, :class:`.Thread`, :class:`.abc.PrivateChannel`]]
            The returned channel or ``None`` if not found.
        """
        return self._connection.get_channel(id)

    def get_partial_messageable(self, id: int, *, type: Optional[ChannelType] = None) -> PartialMessageable:
        """Returns a partial messageable with the given channel ID.

        This is useful if you have a channel_id but don't want to do an API call
        to send messages to it.
        
        .. versionadded:: 2.0

        Parameters
        -----------
        id: :class:`int`
            The channel ID to create a partial messageable for.
        type: Optional[:class:`.ChannelType`]
            The underlying channel type for the partial messageable.

        Returns
        --------
        :class:`.PartialMessageable`
            The partial messageable
        """
        return PartialMessageable(state=self._connection, id=id, type=type)

    def get_stage_instance(self, id: int, /) -> Optional[StageInstance]:
        """Returns a stage instance with the given stage channel ID.

        .. versionadded:: 2.0

        Parameters
        -----------
        id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`.StageInstance`]
            The returns stage instance of ``None`` if not found.
        """
        from .channel import StageChannel

        channel = self._connection.get_channel(id)

        if isinstance(channel, StageChannel):
            return channel.instance

    def get_guild(self, id: int, /) -> Optional[Guild]:
        """Returns a guild with the given ID.

        Parameters
        -----------
        id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`.Guild`]
            The guild or ``None`` if not found.
        """
        return self._connection._get_guild(id)

    def get_user(self, id: int, /) -> Optional[User]:
        """Returns a user with the given ID.

        Parameters
        -----------
        id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`~discord.User`]
            The user or ``None`` if not found.
        """
        return self._connection.get_user(id)

    def get_emoji(self, id: int, /) -> Optional[Emoji]:
        """Returns an emoji with the given ID.

        Parameters
        -----------
        id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`.Emoji`]
            The custom emoji or ``None`` if not found.
        """
        return self._connection.get_emoji(id)

    def get_sticker(self, id: int, /) -> Optional[GuildSticker]:
        """Returns a guild sticker with the given ID.

        .. versionadded:: 2.0

        .. note::

            To retrieve standard stickers, use :meth:`.fetch_sticker`.
            or :meth:`.fetch_premium_sticker_packs`.

        Returns
        --------
        Optional[:class:`.GuildSticker`]
            The sticker or ``None`` if not found.
        """
        return self._connection.get_sticker(id)

    def get_all_channels(self) -> Generator[GuildChannel, None, None]:
        """A generator that retrieves every :class:`.abc.GuildChannel` the client can 'access'.

        This is equivalent to: ::

            for guild in client.guilds:
                for channel in guild.channels:
                    yield channel

        .. note::

            Just because you receive a :class:`.abc.GuildChannel` does not mean that
            you can communicate in said channel. :meth:`.abc.GuildChannel.permissions_for` should
            be used for that.

        Yields
        ------
        :class:`.abc.GuildChannel`
            A channel the client can 'access'.
        """

        for guild in self.guilds:
            yield from guild.channels

    def get_all_members(self) -> Generator[Member, None, None]:
        """Returns a generator with every :class:`.Member` the client can see.

        This is equivalent to: ::

            for guild in client.guilds:
                for member in guild.members:
                    yield member

        Yields
        ------
        :class:`.Member`
            A member the client can see.
        """
        for guild in self.guilds:
            yield from guild.members

    # listeners/waiters

    async def wait_until_ready(self) -> None:
        """|coro|

        Waits until the client's internal cache is all ready.
        """
        await self._ready.wait()

    def wait_for(
        self,
        event: str,
        *,
        check: Optional[Callable[..., bool]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """|coro|

        Waits for a WebSocket event to be dispatched.

        This could be used to wait for a user to reply to a message,
        or to react to a message, or to edit a message in a self-contained
        way.

        The ``timeout`` parameter is passed onto :func:`asyncio.wait_for`. By default,
        it does not timeout. Note that this does propagate the
        :exc:`asyncio.TimeoutError` for you in case of timeout and is provided for
        ease of use.

        In case the event returns multiple arguments, a :class:`tuple` containing those
        arguments is returned instead. Please check the
        :ref:`documentation <discord-api-events>` for a list of events and their
        parameters.

        This function returns the **first event that meets the requirements**.

        Examples
        ---------

        Waiting for a user reply: ::

            @client.event
            async def on_message(message):
                if message.content.startswith('$greet'):
                    channel = message.channel
                    await channel.send('Say hello!')

                    def check(m):
                        return m.content == 'hello' and m.channel == channel

                    msg = await client.wait_for('message', check=check)
                    await channel.send(f'Hello {msg.author}!')

        Waiting for a thumbs up reaction from the message author: ::

            @client.event
            async def on_message(message):
                if message.content.startswith('$thumb'):
                    channel = message.channel
                    await channel.send('Send me that \N{THUMBS UP SIGN} reaction, mate')

                    def check(reaction, user):
                        return user == message.author and str(reaction.emoji) == '\N{THUMBS UP SIGN}'

                    try:
                        reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
                    except asyncio.TimeoutError:
                        await channel.send('\N{THUMBS DOWN SIGN}')
                    else:
                        await channel.send('\N{THUMBS UP SIGN}')


        Parameters
        ------------
        event: :class:`str`
            The event name, similar to the :ref:`event reference <discord-api-events>`,
            but without the ``on_`` prefix, to wait for.
        check: Optional[Callable[..., :class:`bool`]]
            A predicate to check what to wait for. The arguments must meet the
            parameters of the event being waited for.
        timeout: Optional[:class:`float`]
            The number of seconds to wait before timing out and raising
            :exc:`asyncio.TimeoutError`.

        Raises
        -------
        asyncio.TimeoutError
            If a timeout is provided and it was reached.

        Returns
        --------
        Any
            Returns no arguments, a single argument, or a :class:`tuple` of multiple
            arguments that mirrors the parameters passed in the
            :ref:`event reference <discord-api-events>`.
        """

        future = self.loop.create_future()
        if check is None:
            def _check(*args):
                return True
            check = _check

        ev = event.lower()
        try:
            listeners = self._listeners[ev]
        except KeyError:
            listeners = []
            self._listeners[ev] = listeners

        listeners.append((future, check))
        return asyncio.wait_for(future, timeout)

    # event registration

    def event(self, coro: Coro) -> Coro:
        """A decorator that registers an event to listen to.

        You can find more info about the events on the :ref:`documentation below <discord-api-events>`.

        The events must be a :ref:`coroutine <coroutine>`, if not, :exc:`TypeError` is raised.

        Example
        ---------

        .. code-block:: python3

            @client.event
            async def on_ready():
                print('Ready!')

        Raises
        --------
        TypeError
            The coroutine passed is not actually a coroutine.
        """

        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('event registered must be a coroutine function')

        setattr(self, coro.__name__, coro)
        _log.debug('%s has successfully been registered as an event', coro.__name__)
        return coro

    async def change_presence(
        self,
        *,
        activity: Optional[BaseActivity] = None,
        status: Optional[Status] = None,
    ):
        """|coro|

        Changes the client's presence.

        Example
        ---------

        .. code-block:: python3

            game = discord.Game("with the API")
            await client.change_presence(status=discord.Status.idle, activity=game)

        .. versionchanged:: 2.0
            Removed the ``afk`` keyword-only parameter.

        Parameters
        ----------
        activity: Optional[:class:`.BaseActivity`]
            The activity being done. ``None`` if no currently active activity is done.
        status: Optional[:class:`.Status`]
            Indicates what status to change to. If ``None``, then
            :attr:`.Status.online` is used.

        Raises
        ------
        :exc:`.InvalidArgument`
            If the ``activity`` parameter is not the proper type.
        """

        if status is None:
            status_str = 'online'
            status = Status.online
        elif status is Status.offline:
            status_str = 'invisible'
            status = Status.offline
        else:
            status_str = str(status)

        await self.ws.change_presence(activity=activity, status=status_str)

        for guild in self._connection.guilds:
            me = guild.me
            if me is None:
                continue

            if activity is not None:
                me.activities = (activity,)
            else:
                me.activities = ()

            me.status = status

    # Guild stuff

    def fetch_guilds(
        self,
        *,
        limit: Optional[int] = 100,
        before: SnowflakeTime = None,
        after: SnowflakeTime = None
    ) -> GuildIterator:
        """Retrieves an :class:`.AsyncIterator` that enables receiving your guilds.

        .. note::

            Using this, you will only receive :attr:`.Guild.owner`, :attr:`.Guild.icon`,
            :attr:`.Guild.id`, and :attr:`.Guild.name` per :class:`.Guild`.

        .. note::

            This method is an API call. For general usage, consider :attr:`guilds` instead.

        Examples
        ---------

        Usage ::

            async for guild in client.fetch_guilds(limit=150):
                print(guild.name)

        Flattening into a list ::

            guilds = await client.fetch_guilds(limit=150).flatten()
            # guilds is now a list of Guild...

        All parameters are optional.

        Parameters
        -----------
        limit: Optional[:class:`int`]
            The number of guilds to retrieve.
            If ``None``, it retrieves every guild you have access to. Note, however,
            that this would make it a slow operation.
            Defaults to ``100``.
        before: Union[:class:`.abc.Snowflake`, :class:`datetime.datetime`]
            Retrieves guilds before this date or object.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.
        after: Union[:class:`.abc.Snowflake`, :class:`datetime.datetime`]
            Retrieve guilds after this date or object.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.

        Raises
        ------
        :exc:`.HTTPException`
            Getting the guilds failed.

        Yields
        --------
        :class:`.Guild`
            The guild with the guild data parsed.
        """
        return GuildIterator(self, limit=limit, before=before, after=after)

    async def fetch_template(self, code: Union[Template, str]) -> Template:
        """|coro|

        Gets a :class:`.Template` from a discord.new URL or code.

        Parameters
        -----------
        code: Union[:class:`.Template`, :class:`str`]
            The Discord Template Code or URL (must be a discord.new URL).

        Raises
        -------
        :exc:`.NotFound`
            The template is invalid.
        :exc:`.HTTPException`
            Getting the template failed.

        Returns
        --------
        :class:`.Template`
            The template from the URL/code.
        """
        code = utils.resolve_template(code)
        data = await self.http.get_template(code)
        return Template(data=data, state=self._connection) # type: ignore

    async def fetch_guild(self, guild_id: int, /) -> Guild:
        """|coro|

        Retrieves a :class:`.Guild` from an ID.

        .. note::

            Using this, you will **not** receive :attr:`.Guild.channels`, :attr:`.Guild.members`,
            :attr:`.Member.activity` and :attr:`.Member.voice` per :class:`.Member`.

        .. note::

            This method is an API call. For general usage, consider :meth:`get_guild` instead.

        Parameters
        -----------
        guild_id: :class:`int`
            The guild's ID to fetch from.

        Raises
        ------
        :exc:`.Forbidden`
            You do not have access to the guild.
        :exc:`.HTTPException`
            Getting the guild failed.

        Returns
        --------
        :class:`.Guild`
            The guild from the ID.
        """
        data = await self.http.get_guild(guild_id)
        return Guild(data=data, state=self._connection)

    async def create_guild(
        self,
        *,
        name: str,
        region: Union[VoiceRegion, str] = VoiceRegion.us_west,
        icon: bytes = MISSING,
        code: str = MISSING,
    ) -> Guild:
        """|coro|

        Creates a :class:`.Guild`.

        Bot accounts in more than 10 guilds are not allowed to create guilds.

        Parameters
        ----------
        name: :class:`str`
            The name of the guild.
        region: :class:`.VoiceRegion`
            The region for the voice communication server.
            Defaults to :attr:`.VoiceRegion.us_west`.
        icon: Optional[:class:`bytes`]
            The :term:`py:bytes-like object` representing the icon. See :meth:`.ClientUser.edit`
            for more details on what is expected.
        code: :class:`str`
            The code for a template to create the guild with.

            .. versionadded:: 1.4

        Raises
        ------
        :exc:`.HTTPException`
            Guild creation failed.
        :exc:`.InvalidArgument`
            Invalid icon image format given. Must be PNG or JPG.

        Returns
        -------
        :class:`.Guild`
            The guild created. This is not the same guild that is
            added to cache.
        """
        if icon is not MISSING:
            icon_base64 = utils._bytes_to_base64_data(icon)
        else:
            icon_base64 = None

        region_value = str(region)

        if code:
            data = await self.http.create_from_template(code, name, region_value, icon_base64)
        else:
            data = await self.http.create_guild(name, region_value, icon_base64)
        return Guild(data=data, state=self._connection)

    async def fetch_stage_instance(self, channel_id: int, /) -> StageInstance:
        """|coro|

        Gets a :class:`.StageInstance` for a stage channel id.

        .. versionadded:: 2.0

        Parameters
        -----------
        channel_id: :class:`int`
            The stage channel ID.

        Raises
        -------
        :exc:`.NotFound`
            The stage instance or channel could not be found.
        :exc:`.HTTPException`
            Getting the stage instance failed.

        Returns
        --------
        :class:`.StageInstance`
            The stage instance from the stage channel ID.
        """
        data = await self.http.get_stage_instance(channel_id)
        guild = self.get_guild(int(data['guild_id']))
        return StageInstance(guild=guild, state=self._connection, data=data)  # type: ignore

    # Invite management

    async def fetch_invite(self, url: Union[Invite, str], *, with_counts: bool = True, with_expiration: bool = True) -> Invite:
        """|coro|

        Gets an :class:`.Invite` from a discord.gg URL or ID.

        .. note::

            If the invite is for a guild you have not joined, the guild and channel
            attributes of the returned :class:`.Invite` will be :class:`.PartialInviteGuild` and
            :class:`.PartialInviteChannel` respectively.

        Parameters
        -----------
        url: Union[:class:`.Invite`, :class:`str`]
            The Discord invite ID or URL (must be a discord.gg URL).
        with_counts: :class:`bool`
            Whether to include count information in the invite. This fills the
            :attr:`.Invite.approximate_member_count` and :attr:`.Invite.approximate_presence_count`
            fields.
        with_expiration: :class:`bool`
            Whether to include the expiration date of the invite. This fills the
            :attr:`.Invite.expires_at` field.

            .. versionadded:: 2.0

        Raises
        -------
        :exc:`.NotFound`
            The invite has expired or is invalid.
        :exc:`.HTTPException`
            Getting the invite failed.

        Returns
        --------
        :class:`.Invite`
            The invite from the URL/ID.
        """

        invite_id = utils.resolve_invite(url)
        data = await self.http.get_invite(invite_id, with_counts=with_counts, with_expiration=with_expiration)
        return Invite.from_incomplete(state=self._connection, data=data)

    async def delete_invite(self, invite: Union[Invite, str]) -> None:
        """|coro|

        Revokes an :class:`.Invite`, URL, or ID to an invite.

        You must have the :attr:`~.Permissions.manage_channels` permission in
        the associated guild to do this.

        Parameters
        ----------
        invite: Union[:class:`.Invite`, :class:`str`]
            The invite to revoke.

        Raises
        -------
        :exc:`.Forbidden`
            You do not have permissions to revoke invites.
        :exc:`.NotFound`
            The invite is invalid or expired.
        :exc:`.HTTPException`
            Revoking the invite failed.
        """

        invite_id = utils.resolve_invite(invite)
        await self.http.delete_invite(invite_id)

    # Miscellaneous stuff

    async def fetch_widget(self, guild_id: int, /) -> Widget:
        """|coro|

        Gets a :class:`.Widget` from a guild ID.

        .. note::

            The guild must have the widget enabled to get this information.

        Parameters
        -----------
        guild_id: :class:`int`
            The ID of the guild.

        Raises
        -------
        :exc:`.Forbidden`
            The widget for this guild is disabled.
        :exc:`.HTTPException`
            Retrieving the widget failed.

        Returns
        --------
        :class:`.Widget`
            The guild's widget.
        """
        data = await self.http.get_widget(guild_id)

        return Widget(state=self._connection, data=data)

    async def application_info(self) -> AppInfo:
        """|coro|

        Retrieves the bot's application information.

        Raises
        -------
        :exc:`.HTTPException`
            Retrieving the information failed somehow.

        Returns
        --------
        :class:`.AppInfo`
            The bot's application information.
        """
        data = await self.http.application_info()
        if 'rpc_origins' not in data:
            data['rpc_origins'] = None
        return AppInfo(self._connection, data)

    async def fetch_user(self, user_id: int, /) -> User:
        """|coro|

        Retrieves a :class:`~discord.User` based on their ID.
        You do not have to share any guilds with the user to get this information,
        however many operations do require that you do.

        .. note::

            This method is an API call. If you have :attr:`discord.Intents.members` and member cache enabled, consider :meth:`get_user` instead.

        Parameters
        -----------
        user_id: :class:`int`
            The user's ID to fetch from.

        Raises
        -------
        :exc:`.NotFound`
            A user with this ID does not exist.
        :exc:`.HTTPException`
            Fetching the user failed.

        Returns
        --------
        :class:`~discord.User`
            The user you requested.
        """
        data = await self.http.get_user(user_id)
        return User(state=self._connection, data=data)

    async def fetch_channel(self, channel_id: int, /) -> Union[GuildChannel, PrivateChannel, Thread]:
        """|coro|

        Retrieves a :class:`.abc.GuildChannel`, :class:`.abc.PrivateChannel`, or :class:`.Thread` with the specified ID.

        .. note::

            This method is an API call. For general usage, consider :meth:`get_channel` instead.

        .. versionadded:: 1.2

        Raises
        -------
        :exc:`.InvalidData`
            An unknown channel type was received from Discord.
        :exc:`.HTTPException`
            Retrieving the channel failed.
        :exc:`.NotFound`
            Invalid Channel ID.
        :exc:`.Forbidden`
            You do not have permission to fetch this channel.

        Returns
        --------
        Union[:class:`.abc.GuildChannel`, :class:`.abc.PrivateChannel`, :class:`.Thread`]
            The channel from the ID.
        """
        data = await self.http.get_channel(channel_id)

        factory, ch_type = _threaded_channel_factory(data['type'])
        if factory is None:
            raise InvalidData('Unknown channel type {type} for channel ID {id}.'.format_map(data))

        if ch_type in (ChannelType.group, ChannelType.private):
            # the factory will be a DMChannel or GroupChannel here
            channel = factory(me=self.user, data=data, state=self._connection) # type: ignore
        else:
            # the factory can't be a DMChannel or GroupChannel here
            guild_id = int(data['guild_id']) # type: ignore
            guild = self.get_guild(guild_id) or Object(id=guild_id)
            # GuildChannels expect a Guild, we may be passing an Object
            channel = factory(guild=guild, state=self._connection, data=data) # type: ignore

        return channel

    async def fetch_webhook(self, webhook_id: int, /) -> Webhook:
        """|coro|

        Retrieves a :class:`.Webhook` with the specified ID.

        Raises
        --------
        :exc:`.HTTPException`
            Retrieving the webhook failed.
        :exc:`.NotFound`
            Invalid webhook ID.
        :exc:`.Forbidden`
            You do not have permission to fetch this webhook.

        Returns
        ---------
        :class:`.Webhook`
            The webhook you requested.
        """
        data = await self.http.get_webhook(webhook_id)
        return Webhook.from_state(data, state=self._connection)

    async def fetch_sticker(self, sticker_id: int, /) -> Union[StandardSticker, GuildSticker]:
        """|coro|

        Retrieves a :class:`.Sticker` with the specified ID.

        .. versionadded:: 2.0

        Raises
        --------
        :exc:`.HTTPException`
            Retrieving the sticker failed.
        :exc:`.NotFound`
            Invalid sticker ID.

        Returns
        --------
        Union[:class:`.StandardSticker`, :class:`.GuildSticker`]
            The sticker you requested.
        """
        data = await self.http.get_sticker(sticker_id)
        cls, _ = _sticker_factory(data['type'])  # type: ignore
        return cls(state=self._connection, data=data) # type: ignore

    async def fetch_premium_sticker_packs(self) -> List[StickerPack]:
        """|coro|

        Retrieves all available premium sticker packs.

        .. versionadded:: 2.0

        Raises
        -------
        :exc:`.HTTPException`
            Retrieving the sticker packs failed.

        Returns
        ---------
        List[:class:`.StickerPack`]
            All available premium sticker packs.
        """
        data = await self.http.list_premium_sticker_packs()
        return [StickerPack(state=self._connection, data=pack) for pack in data['sticker_packs']]

    async def create_dm(self, user: Snowflake) -> DMChannel:
        """|coro|

        Creates a :class:`.DMChannel` with this user.

        This should be rarely called, as this is done transparently for most
        people.

        .. versionadded:: 2.0

        Parameters
        -----------
        user: :class:`~discord.abc.Snowflake`
            The user to create a DM with.

        Returns
        -------
        :class:`.DMChannel`
            The channel that was created.
        """
        state = self._connection
        found = state._get_private_channel_by_user(user.id)
        if found:
            return found

        data = await state.http.start_private_message(user.id)
        return state.add_dm_channel(data)

    def add_view(self, view: View, *, message_id: Optional[int] = None) -> None:
        """Registers a :class:`~discord.ui.View` for persistent listening.

        This method should be used for when a view is comprised of components
        that last longer than the lifecycle of the program.
        
        .. versionadded:: 2.0

        Parameters
        ------------
        view: :class:`discord.ui.View`
            The view to register for dispatching.
        message_id: Optional[:class:`int`]
            The message ID that the view is attached to. This is currently used to
            refresh the view's state during message update events. If not given
            then message update events are not propagated for the view.

        Raises
        -------
        TypeError
            A view was not passed.
        ValueError
            The view is not persistent. A persistent view has no timeout
            and all their components have an explicitly provided custom_id.
        """

        if not isinstance(view, View):
            raise TypeError(f'expected an instance of View not {view.__class__!r}')

        if not view.is_persistent():
            raise ValueError('View is not persistent. Items need to have a custom_id set and View must have no timeout')

        self._connection.store_view(view, message_id)

    @property
    def persistent_views(self) -> Sequence[View]:
        """Sequence[:class:`.View`]: A sequence of persistent views added to the client.
        
        .. versionadded:: 2.0
        """
        return self._connection.persistent_views

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

import inspect
import discord.utils

import typing
from typing import Any, Callable, ClassVar, Dict, Generator, List, Optional, TYPE_CHECKING, Tuple, TypeVar, Type

import discord

from ...error import IncorrectFormat, IncorrectGuildIDType
from ...model import CogBaseCommandObject, CogComponentCallbackObject, CogSubcommandObject
from ...InteractionUtils import manage_commands
from ...InteractionUtils.manage_components import get_components_ids, get_messages_ids

from ._types import _BaseCommand

if TYPE_CHECKING:
    from .bot import BotBase
    from .context import Context
    from .core import Command

__all__ = (
    'CogMeta',
    'Cog',
)

CogT = TypeVar('CogT', bound='Cog')
FuncT = TypeVar('FuncT', bound=Callable[..., Any])

MISSING: Any = discord.utils.MISSING

def cog_interactions(
    *,
    name: str = None,
    description: str = None,
    guild_ids: typing.List[int] = None,
    options: typing.List[dict] = None,
    default_permission: bool = True,
    permissions: typing.Dict[int, list] = None,
    connector: dict = None,
):
    """
    Decorator for Cog to add command interaction.\n
    Almost same as :meth:`.client.Interaction.interaction`.
    Example:
    .. code-block:: python
        class ExampleCog(commands.Cog):
            def __init__(self, bot):
                self.bot = bot
            @cog_ext.cog_slash(name="ping")
            async def ping(self, ctx: SlashContext):
                await ctx.send(content="Pong!")
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
    :param permissions: Dictionary of permissions of the command interaction. Key being target guild_id and value being a list of permissions to apply. Default ``None``.
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

        desc = description or inspect.getdoc(cmd)
        if options is None:
            opts = manage_commands.generate_options(cmd, desc, connector)
        else:
            opts = options

        if guild_ids and not all(isinstance(item, int) for item in guild_ids):
            raise IncorrectGuildIDType(f"The snowflake IDs {guild_ids} given are not a list of integers. Because of discord.py convention, please use integer IDs instead. Furthermore, the command '{name or cmd.__name__}' won't be registered until fixed.")

        _cmd = {
            "func": cmd,
            "description": desc,
            "guild_ids": guild_ids,
            "api_options": opts,
            "default_permission": default_permission,
            "api_permissions": permissions,
            "connector": connector,
            "has_subcommands": False,
        }
        return CogBaseCommandObject(name or cmd.__name__, _cmd)

    return wrapper


def cog_subcommand(
    *,
    base,
    subcommand_group=None,
    name=None,
    description: str = None,
    base_description: str = None,
    base_desc: str = None,
    base_default_permission: bool = True,
    base_permissions: typing.Dict[int, list] = None,
    subcommand_group_description: str = None,
    sub_group_desc: str = None,
    guild_ids: typing.List[int] = None,
    options: typing.List[dict] = None,
    connector: dict = None,
):
    """
    Decorator for Cog to add subcommand.\n
    Almost same as :meth:`.client.Interaction.subcommand`.
    Example:
    .. code-block:: python
        class ExampleCog(commands.Cog):
            def __init__(self, bot):
                self.bot = bot
            @cog_ext.cog_subcommand(base="group", name="say")
            async def group_say(self, ctx: SlashContext, text: str):
                await ctx.send(content=text)
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
    :param base_permissions: Dictionary of permissions of the command interaction. Key being target guild_id and value being a list of permissions to apply. Default ``None``.
    :type base_permissions: dict
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
    guild_ids = guild_ids if guild_ids else []
    if not base_permissions:
        base_permissions = {}

    def wrapper(cmd):
        decorator_permissions = getattr(cmd, "__permissions__", None)
        if decorator_permissions:
            base_permissions.update(decorator_permissions)

        desc = description or inspect.getdoc(cmd)
        if options is None:
            opts = manage_commands.generate_options(cmd, desc, connector)
        else:
            opts = options

        if guild_ids and not all(isinstance(item, int) for item in guild_ids):
            raise IncorrectGuildIDType(
                f"The snowflake IDs {guild_ids} given are not a list of integers. Because of discord.py convention, please use integer IDs instead. Furthermore, the command '{name or cmd.__name__}' will be deactivated and broken until fixed."
            )

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
            "name": name or cmd.__name__,
            "description": desc,
            "base_desc": base_description,
            "sub_group_desc": subcommand_group_description,
            "guild_ids": guild_ids,
            "api_options": opts,
            "connector": connector,
        }
        return CogSubcommandObject(base, _cmd, subcommand_group, name or cmd.__name__, _sub)

    return wrapper


# I don't feel comfortable with having these right now, they're too buggy even when they were working.


def cog_context_menu(*, name: str, guild_ids: list = None, target: int = 1):
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
        if name == "context":
            raise IncorrectFormat(
                "The name 'context' can not be used to register as a cog context menu,"
                "as this conflicts with this lib's checks. Please use a different name instead."
            )

        _cmd = {
            "default_permission": None,
            "has_permissions": None,
            "name": name,
            "type": target,
            "func": cmd,
            "description": "",
            "guild_ids": guild_ids,
            "api_options": [],
            "connector": {},
            "has_subcommands": False,
            "api_permissions": {},
        }
        return CogBaseCommandObject(name or cmd.__name__, _cmd, target)

    return wrapper


def permission(guild_id: int, permissions: list):
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


def cog_component(
    *,
    messages: typing.Union[int, discord.Message, list] = None,
    components: typing.Union[str, dict, list] = None,
    use_callback_name=True,
    component_type: int = None,
):
    """
    Decorator for component callbacks in cogs.\n
    Almost same as :meth:`.client.Interaction.component_callback`.
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

    def wrapper(callback):
        nonlocal custom_ids

        if use_callback_name and custom_ids == [None]:
            custom_ids = [callback.__name__]

        if message_ids == [None] and custom_ids == [None]:
            raise IncorrectFormat("You must specify messages or components (or both)")

        return CogComponentCallbackObject(
            callback,
            message_ids=message_ids,
            custom_ids=custom_ids,
            component_type=component_type,
        )

    return wrapper

class CogMeta(type):
    """A metaclass for defining a cog.

    Note that you should probably not use this directly. It is exposed
    purely for documentation purposes along with making custom metaclasses to intermix
    with other metaclasses such as the :class:`abc.ABCMeta` metaclass.

    For example, to create an abstract cog mixin class, the following would be done.

    .. code-block:: python3

        import abc

        class CogABCMeta(commands.CogMeta, abc.ABCMeta):
            pass

        class SomeMixin(metaclass=abc.ABCMeta):
            pass

        class SomeCogMixin(SomeMixin, commands.Cog, metaclass=CogABCMeta):
            pass

    .. note::

        When passing an attribute of a metaclass that is documented below, note
        that you must pass it as a keyword-only argument to the class creation
        like the following example:

        .. code-block:: python3

            class MyCog(commands.Cog, name='My Cog'):
                pass

    Attributes
    -----------
    name: :class:`str`
        The cog name. By default, it is the name of the class with no modification.
    description: :class:`str`
        The cog description. By default, it is the cleaned docstring of the class.

        .. versionadded:: 1.6

    command_attrs: :class:`dict`
        A list of attributes to apply to every command inside this cog. The dictionary
        is passed into the :class:`Command` options at ``__init__``.
        If you specify attributes inside the command attribute in the class, it will
        override the one specified inside this attribute. For example:

        .. code-block:: python3

            class MyCog(commands.Cog, command_attrs=dict(hidden=True)):
                @commands.command()
                async def foo(self, ctx):
                    pass # hidden -> True

                @commands.command(hidden=False)
                async def bar(self, ctx):
                    pass # hidden -> False
    """
    __cog_name__: str
    __cog_settings__: Dict[str, Any]
    __cog_commands__: List[Command]
    __cog_listeners__: List[Tuple[str, str]]

    def __new__(cls: Type[CogMeta], *args: Any, **kwargs: Any) -> CogMeta:
        name, bases, attrs = args
        attrs['__cog_name__'] = kwargs.pop('name', name)
        attrs['__cog_settings__'] = kwargs.pop('command_attrs', {})

        description = kwargs.pop('description', None)
        if description is None:
            description = inspect.cleandoc(attrs.get('__doc__', ''))
        attrs['__cog_description__'] = description

        commands = {}
        listeners = {}
        no_bot_cog = 'Commands or listeners must not start with cog_ or bot_ (in method {0.__name__}.{1})'

        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        for base in reversed(new_cls.__mro__):
            for elem, value in base.__dict__.items():
                if elem in commands:
                    del commands[elem]
                if elem in listeners:
                    del listeners[elem]

                is_static_method = isinstance(value, staticmethod)
                if is_static_method:
                    value = value.__func__
                if isinstance(value, _BaseCommand):
                    if is_static_method:
                        raise TypeError(f'Command in method {base}.{elem!r} must not be staticmethod.')
                    if elem.startswith(('cog_', 'bot_')):
                        raise TypeError(no_bot_cog.format(base, elem))
                    commands[elem] = value
                elif inspect.iscoroutinefunction(value):
                    try:
                        getattr(value, '__cog_listener__')
                    except AttributeError:
                        continue
                    else:
                        if elem.startswith(('cog_', 'bot_')):
                            raise TypeError(no_bot_cog.format(base, elem))
                        listeners[elem] = value

        new_cls.__cog_commands__ = list(commands.values()) # this will be copied in Cog.__new__

        listeners_as_list = []
        for listener in listeners.values():
            for listener_name in listener.__cog_listener_names__:
                # I use __name__ instead of just storing the value so I can inject
                # the self attribute when the time comes to add them to the bot
                listeners_as_list.append((listener_name, listener.__name__))

        new_cls.__cog_listeners__ = listeners_as_list
        return new_cls

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args)

    @classmethod
    def qualified_name(cls) -> str:
        return cls.__cog_name__

def _cog_special_method(func: FuncT) -> FuncT:
    func.__cog_special_method__ = None
    return func

class Cog(metaclass=CogMeta):
    """The base class that all cogs must inherit from.

    A cog is a collection of commands, listeners, and optional state to
    help group commands together. More information on them can be found on
    the :ref:`ext_commands_cogs` page.

    When inheriting from this class, the options shown in :class:`CogMeta`
    are equally valid here.
    """
    __cog_name__: ClassVar[str]
    __cog_settings__: ClassVar[Dict[str, Any]]
    __cog_commands__: ClassVar[List[Command]]
    __cog_listeners__: ClassVar[List[Tuple[str, str]]]

    def __new__(cls: Type[CogT], *args: Any, **kwargs: Any) -> CogT:
        # For issue 426, we need to store a copy of the command objects
        # since we modify them to inject `self` to them.
        # To do this, we need to interfere with the Cog creation process.
        self = super().__new__(cls)
        cmd_attrs = cls.__cog_settings__

        # Either update the command with the cog provided defaults or copy it.
        # r.e type ignore, type-checker complains about overriding a ClassVar
        self.__cog_commands__ = tuple(c._update_copy(cmd_attrs) for c in cls.__cog_commands__)  # type: ignore

        lookup = {
            cmd.qualified_name: cmd
            for cmd in self.__cog_commands__
        }

        # Update the Command instances dynamically as well
        for command in self.__cog_commands__:
            setattr(self, command.callback.__name__, command)
            parent = command.parent
            if parent is not None:
                # Get the latest parent reference
                parent = lookup[parent.qualified_name]  # type: ignore

                # Update our parent's reference to our self
                parent.remove_command(command.name)  # type: ignore
                parent.add_command(command)  # type: ignore

        return self

    def get_commands(self) -> List[Command]:
        r"""
        Returns
        --------
        List[:class:`.Command`]
            A :class:`list` of :class:`.Command`\s that are
            defined inside this cog.

            .. note::

                This does not include subcommands.
        """
        return [c for c in self.__cog_commands__ if c.parent is None]

    @property
    def qualified_name(self) -> str:
        """:class:`str`: Returns the cog's specified name, not the class name."""
        return self.__cog_name__

    @property
    def description(self) -> str:
        """:class:`str`: Returns the cog's description, typically the cleaned docstring."""
        return self.__cog_description__

    @description.setter
    def description(self, description: str) -> None:
        """A Description of a Cog."""
        self.__cog_description__ = description

    def walk_commands(self) -> Generator[Command, None, None]:
        """An iterator that recursively walks through this cog's commands and subcommands.

        Yields
        ------
        Union[:class:`.Command`, :class:`.Group`]
            A command or group from the cog.
        """
        from .core import GroupMixin
        for command in self.__cog_commands__:
            if command.parent is None:
                yield command
                if isinstance(command, GroupMixin):
                    yield from command.walk_commands()

    def get_listeners(self) -> List[Tuple[str, Callable[..., Any]]]:
        """Returns a :class:`list` of (name, function) listener pairs that are defined in this cog.

        Returns
        --------
        List[Tuple[:class:`str`, :ref:`coroutine <coroutine>`]]
            The listeners defined in this cog.
        """
        return [(name, getattr(self, method_name)) for name, method_name in self.__cog_listeners__]

    @classmethod
    def _get_overridden_method(cls, method: FuncT) -> Optional[FuncT]:
        """Return None if the method is not overridden. Otherwise returns the overridden method."""
        return getattr(method.__func__, '__cog_special_method__', method)

    @classmethod
    def listener(cls, name: str = MISSING) -> Callable[[FuncT], FuncT]:
        """A decorator that marks a function as a listener.

        This is the cog equivalent of :meth:`.Bot.listen`.

        Parameters
        ------------
        name: :class:`str`
            The name of the event being listened to. If not provided, it
            defaults to the function's name.

        Raises
        --------
        TypeError
            The function is not a coroutine function or a string was not passed as
            the name.
        """

        if name is not MISSING and not isinstance(name, str):
            raise TypeError(f'Cog.listener expected str but received {name.__class__.__name__!r} instead.')

        def decorator(func: FuncT) -> FuncT:
            actual = func
            if isinstance(actual, staticmethod):
                actual = actual.__func__
            if not inspect.iscoroutinefunction(actual):
                raise TypeError('Listener function must be a coroutine function.')
            actual.__cog_listener__ = True
            to_assign = name or actual.__name__
            try:
                actual.__cog_listener_names__.append(to_assign)
            except AttributeError:
                actual.__cog_listener_names__ = [to_assign]
            # we have to return `func` instead of `actual` because
            # we need the type to be `staticmethod` for the metaclass
            # to pick it up but the metaclass unfurls the function and
            # thus the assignments need to be on the actual function
            return func
        return decorator

    def has_error_handler(self) -> bool:
        """:class:`bool`: Checks whether the cog has an error handler.

        .. versionadded:: 1.7
        """
        return not hasattr(self.cog_command_error.__func__, '__cog_special_method__')

    @_cog_special_method
    def cog_unload(self) -> None:
        """A special method that is called when the cog gets removed.

        This function **cannot** be a coroutine. It must be a regular
        function.

        Subclasses must replace this if they want special unloading behaviour.
        """
        pass

    @_cog_special_method
    def bot_check_once(self, ctx: Context) -> bool:
        """A special method that registers as a :meth:`.Bot.check_once`
        check.

        This function **can** be a coroutine and must take a sole parameter,
        ``ctx``, to represent the :class:`.Context`.
        """
        return True

    @_cog_special_method
    def bot_check(self, ctx: Context) -> bool:
        """A special method that registers as a :meth:`.Bot.check`
        check.

        This function **can** be a coroutine and must take a sole parameter,
        ``ctx``, to represent the :class:`.Context`.
        """
        return True

    @_cog_special_method
    def cog_check(self, ctx: Context) -> bool:
        """A special method that registers as a :func:`~discord.ext.commands.check`
        for every command and subcommand in this cog.

        This function **can** be a coroutine and must take a sole parameter,
        ``ctx``, to represent the :class:`.Context`.
        """
        return True

    @_cog_special_method
    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        """A special method that is called whenever an error
        is dispatched inside this cog.

        This is similar to :func:`.on_command_error` except only applying
        to the commands inside this cog.

        This **must** be a coroutine.

        Parameters
        -----------
        ctx: :class:`.Context`
            The invocation context where the error happened.
        error: :class:`CommandError`
            The error that happened.
        """
        pass

    @_cog_special_method
    async def cog_before_invoke(self, ctx: Context) -> None:
        """A special method that acts as a cog local pre-invoke hook.

        This is similar to :meth:`.Command.before_invoke`.

        This **must** be a coroutine.

        Parameters
        -----------
        ctx: :class:`.Context`
            The invocation context.
        """
        pass

    @_cog_special_method
    async def cog_after_invoke(self, ctx: Context) -> None:
        """A special method that acts as a cog local post-invoke hook.

        This is similar to :meth:`.Command.after_invoke`.

        This **must** be a coroutine.

        Parameters
        -----------
        ctx: :class:`.Context`
            The invocation context.
        """
        pass

    def _inject(self: CogT, bot: BotBase) -> CogT:
        cls = self.__class__

        # realistically, the only thing that can cause loading errors
        # is essentially just the command loading, which raises if there are
        # duplicates. When this condition is met, we want to undo all what
        # we've added so far for some form of atomic loading.
        for index, command in enumerate(self.__cog_commands__):
            command.cog = self
            if command.parent is None:
                try:
                    bot.add_command(command)
                except Exception as e:
                    # undo our additions
                    for to_undo in self.__cog_commands__[:index]:
                        if to_undo.parent is None:
                            bot.remove_command(to_undo.name)
                    raise e

        # check if we're overriding the default
        if cls.bot_check is not Cog.bot_check:
            bot.add_check(self.bot_check)

        if cls.bot_check_once is not Cog.bot_check_once:
            bot.add_check(self.bot_check_once, call_once=True)

        # while Bot.add_listener can raise if it's not a coroutine,
        # this precondition is already met by the listener decorator
        # already, thus this should never raise.
        # Outside of, memory errors and the like...
        for name, method_name in self.__cog_listeners__:
            bot.add_listener(getattr(self, method_name), name)

        return self

    def _eject(self, bot: BotBase) -> None:
        cls = self.__class__

        try:
            for command in self.__cog_commands__:
                if command.parent is None:
                    bot.remove_command(command.name)

            for _, method_name in self.__cog_listeners__:
                bot.remove_listener(getattr(self, method_name))

            if cls.bot_check is not Cog.bot_check:
                bot.remove_check(self.bot_check)

            if cls.bot_check_once is not Cog.bot_check_once:
                bot.remove_check(self.bot_check_once, call_once=True)
        finally:
            try:
                self.cog_unload()
            except Exception:
                pass

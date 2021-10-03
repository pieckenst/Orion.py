Orion.py
==========

.. image:: https://discord.com/api/guilds/881095332434440224/embed.png
   :target: https://discord.gg/zzdEGHbkTj
   :alt: Discord server invite
.. image:: https://img.shields.io/badge/Made%20with-Python-1f425f.svg
   :target: https://www.python.org/
   :alt: Made with Python
.. image:: https://img.shields.io/pypi/v/orion.py.svg
   :target: https://pypi.python.org/pypi/orion.py
   :alt: PyPI version info
.. image:: https://img.shields.io/pypi/pyversions/orion.py.svg
   :target: https://pypi.python.org/pypi/orion.py
   :alt: PyPI supported Python versions
.. image:: https://img.shields.io/tokei/lines/github/Senarc-Studios/Orion.py?style=plastic
    :alt: Lines of code
.. image:: https://badge-size.herokuapp.com/Senarc-Studios/Orion.py/master/
   :alt: Size of package
   :target: https://github.com/Naereen/StrapDown.js/blob/master
.. image:: https://img.shields.io/github/issues/Senarc-Studios/Orion.py?style=plastic
    :alt: GitHub issues   
    :target: https://github.com/Senarc-Studios/Orion.py/issues
.. image:: https://img.shields.io/github/forks/Senarc-Studios/Orion.py?style=plastic
    :alt: GitHub forks   
    :target: https://github.com/Senarc-Studios/Orion.py/network
.. image:: https://img.shields.io/github/stars/Senarc-Studios/Orion.py?style=plastic
    :alt: GitHub stars   
    :target: https://github.com/Senarc-Studios/Orion.py/stargazers
.. image:: https://img.shields.io/github/license/Senarc-Studios/Orion.py?style=plastic
    :alt: GitHub license   
    :target: https://github.com/Senarc-Studios/Orion.py/blob/master/LICENSE

A modern, easy to use, feature-rich, and async ready API wrapper improved and revived from original discord.py, borrowing code from other libraries such as *`Pycord<https://github.com/Pycord-Development/pycord/>`__ and [Enchanced Discord.py](https://github.com/iDevision/enhanced-discord.py)

Key Features
-------------

- Modern Python API async wrapper.
- Proper rate limit handling.
- Optimised in both speed and memory.
- Implements new discord features into Bots.
- Improved methods with more features.

Installing
----------

**Python 3.8 or higher is required**

To install the library without full voice support, you can just run the following command:

.. code:: sh

    # Linux/macOS
    python3 -m pip install -U orion.py

    # Windows
    py -3 -m pip install -U orion.py

Otherwise to get voice support you should run the following command:

.. code:: sh

    # Linux/macOS
    python3 -m pip install -U "orion.py[voice]"

    # Windows
    py -3 -m pip install -U orion.py[voice]


To install the development version, do the following:

.. code:: sh


    $ git clone https://github.com/Senarc-Studios/orion.py@Development
    $ cd orion.py
    $ python3 -m pip install -U .[voice]


Optional Packages
~~~~~~~~~~~~~~~~~~

* `PyNaCl <https://pypi.org/project/PyNaCl/>`__ (for voice support)

Please note that on Linux installing voice you must install the following packages VIA your favourite package manager (e.g. ``apt``, ``dnf``, etc) before running the above commands:

* libffi-dev (or ``libffi-devel`` on some systems)
* python-dev (e.g. ``python3.6-dev`` for Python 3.6)

Quick Example
--------------

.. code:: py

    import discord

    class MyClient(discord.Client):
        async def on_ready(self):
            print('Logged on as', self.user)

        async def on_message(self, message):
            # don't respond to ourselves
            if message.author == self.user:
                return

            if message.content == 'ping':
                await message.channel.send('pong')

    client = MyClient()
    client.run('your-token-here')

Bot Example
~~~~~~~~~~~~~

.. code:: py

    import discord
    from discord.ext import commands

    bot = commands.Bot(command_prefix='!', slash_interactions=True)

    @bot.command(slash_interaction=True, message_command=True)
    async def ping(ctx):
        await ctx.send('pong')

    bot.run('your-token-here')

You can find more examples in the examples directory.

Links
------

- `Documentation <https://discordpy.readthedocs.io/en/latest/index.html>`_
- `Official Discord Server <https://discord.gg/zzdEGHbkTj>`_
- `Discord API <https://discord.gg/discord-api>`_

Outsourced Credits
------------------

`Gnome <https://github.com/Gnome-py>`_ from `enhanced discord.py <https://github.com/iDevision/enhanced-discord.py>`_

"""
The MIT License (MIT)

Copyright (c) 2021-present Benitz

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

from datetime import datetime
from typing import TypeVar

__all__ = (
    'Timestamp'
)

T = TypeVar('T', bound='Timestamp')

class Timestamp:
    """Represents timestamp embedded messages(not embeds).

    Attributes
    -----------
    convert_to_timestamp: :class:`str`
        Converts datetime into timestamp message.
    convert_to_datetime: :class:`str`
        Converts timestamp into datetime string. Datetime formate: '%d/%m/%Y - %H:%M:%S'
    now: :class:`str`
        The timestamp message of the current time.

        .. note::

            All datetimes are supposed to be in the formate '%d/%m/%Y - %H:%M:%S'

            These timestamps are made for messages that will be sent in discord, therefore '<t:>' is added
            to the message for discord's timestamps.

            This doesn't work as embed timestamps.

        .. versionadded:: 2.2
    """

    @property
    async def convert_to_timestamp(date: datetime):
        """
        convert_to_timestamp: :class:`str`
            Converts datetime into timestamp message.
        .. versionadded:: 2.2
        """
        date = datetime.strptime(date, "%d/%m/%Y - %H:%M:%S")
        return "<t:" + f"{int(date.timestamp)}>"

    @property
    async def now():
        """
        convert_to_datetime: :class:`str`
            Converts timestamp into datetime string. Datetime formate: '%d/%m/%Y - %H:%M:%S'
        .. versionadded:: 2.2
        """
        date = (datetime.now()).timestamp()
        return "<t:" + f"{int(date)}>"

    @property
    async def convert_to_date(timestamp: str):
        """
        now: :class:`str`
            The timestamp message of the current datetime.
        .. versionadded:: 2.2
        """
        try:
            timestamp = str(timestamp)
            timestamp = timestamp.replace("<t:", "")
            timestamp = timestamp.replace(">", "")
            try:
                if len(timestamp) != 10:
                    raise TypeError("ERROR: provided 'timestamp' is not a valid timestamp.")
                timestamp = int(timestamp)
            except:
                raise TypeError(f"ERROR: provided 'timestamp' is not a valid timestamp.")
            dt_obj = datetime.fromtimestamp(timestamp)
            dt_obj = str(dt_obj).replace("-", "/")
            dt_obj = dt_obj.replace(" ", " - ")
            return dt_obj
        except Exception as e:
            raise RuntimeError(f"ERROR: 'convert_to_date' function has failed to evaluate, Error:\n{e}")

import datetime

from datetime import datetime
from typing import TypeVar

__all__ = (
    'Timestamp'
)

T = TypeVar('T', bound='Timestamp')

class Timestamp():
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
    async def convert_to_timestamp(date):
        """
        convert_to_timestamp: :class:`str`
            Converts datetime into timestamp message.
        .. versionadded:: 2.2
        """
        date = datetime.strptime(date, "%d/%m/%Y - %H:%M:%S")
        date = datetime.timestamp(date)
        return "<t:" + f"{int(date)}>"

    @property
    async def now():
        """
        convert_to_datetime: :class:`str`
            Converts timestamp into datetime string. Datetime formate: '%d/%m/%Y - %H:%M:%S'
        .. versionadded:: 2.2
        """
        date = datetime.timestamp(datetime.now())
        return "<t:" + f"{int(date)}>"

    @property
    async def convert_to_date(timestamp):
        """
        now: :class:`str`
            The timestamp message of the current time.
        .. versionadded:: 2.2
        """
        try:
            dt_obj = datetime.fromtimestamp(timestamp)
            dt_obj = str(dt_obj).replace("-", "/")
            dt_obj = dt_obj.replace(" ", " - ")
            return dt_obj
        except Exception as e:
            print(f"""An error has occured in 'conver_to_date' function, Error:\n{e}""")
            return None
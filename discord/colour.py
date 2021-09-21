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

import colorsys
import random
from typing import Any, Optional, Tuple, Type, TypeVar, Union

__all__ = (
    'Colour',
    'Color',
)

CT = TypeVar('CT', bound='Colour')


class Colour:
    """Represents a Discord role colour. This class is similar
    to a (red, green, blue) :class:`tuple`.

    There is an alias for this called Color.

    .. container:: operations

        .. describe:: x == y

             Checks if two colours are equal.

        .. describe:: x != y

             Checks if two colours are not equal.

        .. describe:: hash(x)

             Return the colour's hash.

        .. describe:: hex(x)

             Return the colour's hex value.

        .. describe:: str(x)

             Returns the hex format for the colour.

        .. describe:: int(x)

             Returns the raw colour value.

    Attributes
    ------------
    value: :class:`int`
        The raw integer colour value.
    """

    __slots__ = ('value',)

    def __init__(self, value: int):
        if not isinstance(value, int):
            raise TypeError(f'Expected int parameter, received {value.__class__.__name__} instead.')

        self.value: int = value

    def _get_byte(self, byte: int) -> int:
        return (self.value >> (8 * byte)) & 0xff

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Colour) and self.value == other.value

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return f'#{self.value:0>6x}'

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return f'<Colour value={self.value}>'

    def __hash__(self) -> int:
        return hash(self.value)

    def __hex__(self) -> str:
        return hex(self.value)

    @property
    def r(self) -> int:
        """:class:`int`: Returns the red component of the colour."""
        return self._get_byte(2)

    @property
    def g(self) -> int:
        """:class:`int`: Returns the green component of the colour."""
        return self._get_byte(1)

    @property
    def b(self) -> int:
        """:class:`int`: Returns the blue component of the colour."""
        return self._get_byte(0)

    def to_rgb(self) -> Tuple[int, int, int]:
        """Tuple[:class:`int`, :class:`int`, :class:`int`]: Returns an (r, g, b) tuple representing the colour."""
        return (self.r, self.g, self.b)

    @classmethod
    def from_rgb(cls: Type[CT], r: int, g: int, b: int) -> CT:
        """Constructs a :class:`Colour` from an RGB tuple."""
        return cls((r << 16) + (g << 8) + b)

    @classmethod
    def from_hsv(cls: Type[CT], h: float, s: float, v: float) -> CT:
        """Constructs a :class:`Colour` from an HSV tuple."""
        rgb = colorsys.hsv_to_rgb(h, s, v)
        return cls.from_rgb(*(int(x * 255) for x in rgb))

    @classmethod
    def default(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0``."""
        return cls(0)

    @classmethod
    def random(cls: Type[CT], *, seed: Optional[Union[int, str, float, bytes, bytearray]] = None) -> CT:
        """A factory method that returns a :class:`Colour` with a random hue.

        .. note::

            The random algorithm works by choosing a colour with a random hue but
            with maxed out saturation and value.

        .. versionadded:: 1.6

        Parameters
        ------------
        seed: Optional[Union[:class:`int`, :class:`str`, :class:`float`, :class:`bytes`, :class:`bytearray`]]
            The seed to initialize the RNG with. If ``None`` is passed the default RNG is used.

            .. versionadded:: 1.7
        """
        rand = random if seed is None else random.Random(seed)
        return cls.from_hsv(rand.random(), 1, 1)

    @classmethod
    def teal(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x1abc9c``."""
        return cls(0x1abc9c)

    @classmethod
    def dark_teal(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x11806a``."""
        return cls(0x11806a)

    @classmethod
    def brand_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x57F287``.

        .. versionadded:: 2.0
        """
        return cls(0x57F287)

    @classmethod
    def green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x2ecc71``."""
        return cls(0x2ecc71)

    @classmethod
    def dark_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x1f8b4c``."""
        return cls(0x1f8b4c)

    @classmethod
    def dark_blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x206694``."""
        return cls(0x206694)

    @classmethod
    def purple(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x9b59b6``."""
        return cls(0x9b59b6)

    @classmethod
    def dark_purple(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x71368a``."""
        return cls(0x71368a)

    @classmethod
    def magenta(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xe91e63``."""
        return cls(0xe91e63)

    @classmethod
    def dark_magenta(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xad1457``."""
        return cls(0xad1457)

    @classmethod
    def gold(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xf1c40f``."""
        return cls(0xf1c40f)

    @classmethod
    def dark_gold(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xc27c0e``."""
        return cls(0xc27c0e)

    @classmethod
    def dark_orange(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xa84300``."""
        return cls(0xa84300)

    @classmethod
    def brand_red(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xED4245``.

        .. versionadded:: 2.0
        """
        return cls(0xED4245)

    @classmethod
    def red(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xe74c3c``."""
        return cls(0xe74c3c)

    @classmethod
    def dark_red(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x992d22``."""
        return cls(0x992d22)

    @classmethod
    def lighter_grey(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x95a5a6``."""
        return cls(0x95a5a6)

    lighter_gray = lighter_grey

    @classmethod
    def dark_grey(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x607d8b``."""
        return cls(0x607d8b)

    dark_gray = dark_grey

    @classmethod
    def light_grey(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x979c9f``."""
        return cls(0x979c9f)

    light_gray = light_grey

    @classmethod
    def darker_grey(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x546e7a``."""
        return cls(0x546e7a)

    darker_gray = darker_grey

    @classmethod
    def og_blurple(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x7289da``."""
        return cls(0x7289da)

    @classmethod
    def blurple(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x5865F2``."""
        return cls(0x5865F2)

    @classmethod
    def greyple(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x99aab5``."""
        return cls(0x99aab5)

    @classmethod
    def dark_theme(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x36393F``.
        This will appear transparent on Discord's dark theme.

        .. versionadded:: 1.5
        """
        return cls(0x36393F)

    @classmethod
    def yellow(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFEE75C``.

        .. versionadded:: 2.0
        """
        return cls(0xFEE75C)

    @classmethod
    def black(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x000000``.
        This is due to the fact that 0x000000 does not work in all platforms.

        .. versionadded:: 2.0
        """
        return cls(0x000000)

    @classmethod
    def purple_mountains__majesty(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x9D81BA``.

        .. versionadded:: 2.0
        """
        return cls(0x9D81BA)

    @classmethod
    def electric_lime(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xCEFF1D``.

        .. versionadded:: 2.0
        """
        return cls(0xCEFF1D)

    @classmethod
    def chestnut(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xBC5D58``.

        .. versionadded:: 2.0
        """
        return cls(0xBC5D58)

    @classmethod
    def tumbleweed(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xDEAA88``.

        .. versionadded:: 2.0
        """
        return cls(0xDEAA88)

    @classmethod
    def wild_strawberry(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF43A4``.

        .. versionadded:: 2.0
        """
        return cls(0xFF43A4)

    @classmethod
    def shocking_pink(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFB7EFD``.

        .. versionadded:: 2.0
        """
        return cls(0xFB7EFD)

    @classmethod
    def sunglow(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFCF48``.

        .. versionadded:: 2.0
        """
        return cls(0xFFCF48)

    @classmethod
    def razzle_dazzle_rose(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF48D0``.

        .. versionadded:: 2.0
        """
        return cls(0xFF48D0)

    @classmethod
    def wisteria(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xCDA4DE``.

        .. versionadded:: 2.0
        """
        return cls(0xCDA4DE)

    @classmethod
    def razzmatazz(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xE3256B``.

        .. versionadded:: 2.0
        """
        return cls(0xE3256B)

    @classmethod
    def wild_blue_yonder(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xA2ADD0``.

        .. versionadded:: 2.0
        """
        return cls(0xA2ADD0)

    @classmethod
    def laser_lemon(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFEFE22``.

        .. versionadded:: 2.0
        """
        return cls(0xFEFE22)

    @classmethod
    def blush(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xDE5D83``.

        .. versionadded:: 2.0
        """
        return cls(0xDE5D83)

    @classmethod
    def blue_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x0D98BA``.

        .. versionadded:: 2.0
        """
        return cls(0x0D98BA)

    @classmethod
    def blue_bell(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xA2A2D0``.

        .. versionadded:: 2.0
        """
        return cls(0xA2A2D0)

    @classmethod
    def fuzzy_wuzzy(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xCC6666``.

        .. versionadded:: 2.0
        """
        return cls(0xCC6666)

    @classmethod
    def fuchsia(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xC364C5``.

        .. versionadded:: 2.0
        """
        return cls(0xC364C5)

    @classmethod
    def gray(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x95918C``.

        .. versionadded:: 2.0
        """
        return cls(0x95918C)

    @classmethod
    def denim(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x2B6CC4``.

        .. versionadded:: 2.0
        """
        return cls(0x2B6CC4)

    @classmethod
    def peach(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFCFAB``.

        .. versionadded:: 2.0
        """
        return cls(0xFFCFAB)

    @classmethod
    def blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x1F75FE``.

        .. versionadded:: 2.0
        """
        return cls(0x1F75FE)

    @classmethod
    def green_yellow(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xF0E891``.

        .. versionadded:: 2.0
        """
        return cls(0xF0E891)

    @classmethod
    def screamin__green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x76FF7A``.

        .. versionadded:: 2.0
        """
        return cls(0x76FF7A)

    @classmethod
    def canary(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFFF99``.

        .. versionadded:: 2.0
        """
        return cls(0xFFFF99)

    @classmethod
    def caribbean_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x00CC99``.

        .. versionadded:: 2.0
        """
        return cls(0x00CC99)

    @classmethod
    def sepia(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xA5694F``.

        .. versionadded:: 2.0
        """
        return cls(0xA5694F)

    @classmethod
    def almond(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xEFDECD``.

        .. versionadded:: 2.0
        """
        return cls(0xEFDECD)

    @classmethod
    def burnt_orange(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF7F49``.

        .. versionadded:: 2.0
        """
        return cls(0xFF7F49)

    @classmethod
    def mango_tango(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF8243``.

        .. versionadded:: 2.0
        """
        return cls(0xFF8243)

    @classmethod
    def pine_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x158078``.

        .. versionadded:: 2.0
        """
        return cls(0x158078)

    @classmethod
    def silver(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xCDC5C2``.

        .. versionadded:: 2.0
        """
        return cls(0xCDC5C2)

    @classmethod
    def fern(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x71BC78``.

        .. versionadded:: 2.0
        """
        return cls(0x71BC78)

    @classmethod
    def lavender(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFCB4D5``.

        .. versionadded:: 2.0
        """
        return cls(0xFCB4D5)

    @classmethod
    def orchid(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xE6A8D7``.

        .. versionadded:: 2.0
        """
        return cls(0xE6A8D7)

    @classmethod
    def sky_blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x80DAEB``.

        .. versionadded:: 2.0
        """
        return cls(0x80DAEB)

    @classmethod
    def granny_smith_apple(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xA8E4A0``.

        .. versionadded:: 2.0
        """
        return cls(0xA8E4A0)

    @classmethod
    def scarlet(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFC2847``.

        .. versionadded:: 2.0
        """
        return cls(0xFC2847)

    @classmethod
    def brown(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xB4674D``.

        .. versionadded:: 2.0
        """
        return cls(0xB4674D)

    @classmethod
    def red_orange(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF5349``.

        .. versionadded:: 2.0
        """
        return cls(0xFF5349)

    @classmethod
    def vivid_violet(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x8F509D``.

        .. versionadded:: 2.0
        """
        return cls(0x8F509D)

    @classmethod
    def yellow_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xC5E384``.

        .. versionadded:: 2.0
        """
        return cls(0xC5E384)

    @classmethod
    def cadet_blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xB0B7C6``.

        .. versionadded:: 2.0
        """
        return cls(0xB0B7C6)

    @classmethod
    def orange(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF7538``.

        .. versionadded:: 2.0
        """
        return cls(0xFF7538)

    @classmethod
    def neon_carrot(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFA343``.

        .. versionadded:: 2.0
        """
        return cls(0xFFA343)

    @classmethod
    def yellow_orange(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFAE42``.

        .. versionadded:: 2.0
        """
        return cls(0xFFAE42)

    @classmethod
    def red_violet(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xC0448F``.

        .. versionadded:: 2.0
        """
        return cls(0xC0448F)

    @classmethod
    def carnation_pink(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFAACC``.

        .. versionadded:: 2.0
        """
        return cls(0xFFAACC)

    @classmethod
    def turquoise_blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x77DDE7``.

        .. versionadded:: 2.0
        """
        return cls(0x77DDE7)

    @classmethod
    def banana_mania(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFAE7B5``.

        .. versionadded:: 2.0
        """
        return cls(0xFAE7B5)

    @classmethod
    def robin_s_egg_blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x1FCECB``.

        .. versionadded:: 2.0
        """
        return cls(0x1FCECB)

    @classmethod
    def eggplant(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x6E5160``.

        .. versionadded:: 2.0
        """
        return cls(0x6E5160)

    @classmethod
    def white(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFFFFF``.

        .. versionadded:: 2.0
        """
        return cls(0xFFFFFF)

    @classmethod
    def purple_pizzazz(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFE4EDA``.

        .. versionadded:: 2.0
        """
        return cls(0xFE4EDA)

    @classmethod
    def shamrock(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x45CEA2``.

        .. versionadded:: 2.0
        """
        return cls(0x45CEA2)

    @classmethod
    def mountain_meadow(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x30BA8F``.

        .. versionadded:: 2.0
        """
        return cls(0x30BA8F)

    @classmethod
    def sunset_orange(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFD5E53``.

        .. versionadded:: 2.0
        """
        return cls(0xFD5E53)

    @classmethod
    def tickle_me_pink(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFC89AC``.

        .. versionadded:: 2.0
        """
        return cls(0xFC89AC)

    @classmethod
    def manatee(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x979AAA``.

        .. versionadded:: 2.0
        """
        return cls(0x979AAA)

    @classmethod
    def desert_sand(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xEFCDB8``.

        .. versionadded:: 2.0
        """
        return cls(0xEFCDB8)

    @classmethod
    def indigo(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x5D76CB``.

        .. versionadded:: 2.0
        """
        return cls(0x5D76CB)

    @classmethod
    def brick_red(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xCB4154``.

        .. versionadded:: 2.0
        """
        return cls(0xCB4154)

    @classmethod
    def asparagus(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x87A96B``.

        .. versionadded:: 2.0
        """
        return cls(0x87A96B)

    @classmethod
    def blue_violet(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x7366BD``.

        .. versionadded:: 2.0
        """
        return cls(0x7366BD)

    @classmethod
    def dandelion(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFDDB6D``.

        .. versionadded:: 2.0
        """
        return cls(0xFDDB6D)

    @classmethod
    def cotton_candy(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFBCD9``.

        .. versionadded:: 2.0
        """
        return cls(0xFFBCD9)

    @classmethod
    def bittersweet(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFD7C6E``.

        .. versionadded:: 2.0
        """
        return cls(0xFD7C6E)

    @classmethod
    def aquamarine(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x78DBE2``.

        .. versionadded:: 2.0
        """
        return cls(0x78DBE2)

    @classmethod
    def purple_heart(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x7442C8``.

        .. versionadded:: 2.0
        """
        return cls(0x7442C8)

    @classmethod
    def copper(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xDD9475``.

        .. versionadded:: 2.0
        """
        return cls(0xDD9475)

    @classmethod
    def pacific_blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x1CA9C9``.

        .. versionadded:: 2.0
        """
        return cls(0x1CA9C9)

    @classmethod
    def outrageous_orange(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF6E4A``.

        .. versionadded:: 2.0
        """
        return cls(0xFF6E4A)

    @classmethod
    def midnight_blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x1A4876``.

        .. versionadded:: 2.0
        """
        return cls(0x1A4876)

    @classmethod
    def cerulean(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x1DACD6``.

        .. versionadded:: 2.0
        """
        return cls(0x1DACD6)

    @classmethod
    def sea_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x93DFB8``.

        .. versionadded:: 2.0
        """
        return cls(0x93DFB8)

    @classmethod
    def beaver(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x9F8170``.

        .. versionadded:: 2.0
        """
        return cls(0x9F8170)

    @classmethod
    def wild_watermelon(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFC6C85``.

        .. versionadded:: 2.0
        """
        return cls(0xFC6C85)

    @classmethod
    def cornflower(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x9ACEEB``.

        .. versionadded:: 2.0
        """
        return cls(0x9ACEEB)

    @classmethod
    def royal_purple(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x7851A9``.

        .. versionadded:: 2.0
        """
        return cls(0x7851A9)

    @classmethod
    def salmon(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF9BAA``.

        .. versionadded:: 2.0
        """
        return cls(0xFF9BAA)

    @classmethod
    def unmellow_yellow(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFFF66``.

        .. versionadded:: 2.0
        """
        return cls(0xFFFF66)

    @classmethod
    def plum(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x8E4585``.

        .. versionadded:: 2.0
        """
        return cls(0x8E4585)

    @classmethod
    def mahogany(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xCD4A4C``.

        .. versionadded:: 2.0
        """
        return cls(0xCD4A4C)

    @classmethod
    def raw_sienna(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xD68A59``.

        .. versionadded:: 2.0
        """
        return cls(0xD68A59)

    @classmethod
    def spring_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xECEABE``.

        .. versionadded:: 2.0
        """
        return cls(0xECEABE)

    @classmethod
    def cerise(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xDD4492``.

        .. versionadded:: 2.0
        """
        return cls(0xDD4492)

    @classmethod
    def tan(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFAA76C``.

        .. versionadded:: 2.0
        """
        return cls(0xFAA76C)

    @classmethod
    def jazzberry_jam(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xCA3767``.

        .. versionadded:: 2.0
        """
        return cls(0xCA3767)

    @classmethod
    def periwinkle(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xC5D0E6``.

        .. versionadded:: 2.0
        """
        return cls(0xC5D0E6)

    @classmethod
    def pink_sherbert(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xF78FA7``.

        .. versionadded:: 2.0
        """
        return cls(0xF78FA7)

    @classmethod
    def melon(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFDBCB4``.

        .. versionadded:: 2.0
        """
        return cls(0xFDBCB4)

    @classmethod
    def jungle_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x3BB08F``.

        .. versionadded:: 2.0
        """
        return cls(0x3BB08F)

    @classmethod
    def hot_magenta(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF1DCE``.

        .. versionadded:: 2.0
        """
        return cls(0xFF1DCE)

    @classmethod
    def apricot(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFDD9B5``.

        .. versionadded:: 2.0
        """
        return cls(0xFDD9B5)

    @classmethod
    def navy_blue(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x1974D2``.

        .. versionadded:: 2.0
        """
        return cls(0x1974D2)

    @classmethod
    def goldenrod(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFCD975``.

        .. versionadded:: 2.0
        """
        return cls(0xFCD975)

    @classmethod
    def tropical_rain_forest(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x17806D``.

        .. versionadded:: 2.0
        """
        return cls(0x17806D)

    @classmethod
    def violet_red(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xF75394``.

        .. versionadded:: 2.0
        """
        return cls(0xF75394)

    @classmethod
    def vivid_tangerine(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFA089``.

        .. versionadded:: 2.0
        """
        return cls(0xFFA089)

    @classmethod
    def olive_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xBAB86C``.

        .. versionadded:: 2.0
        """
        return cls(0xBAB86C)

    @classmethod
    def inchworm(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xB2EC5D``.

        .. versionadded:: 2.0
        """
        return cls(0xB2EC5D)

    @classmethod
    def forest_green(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x6DAE81``.

        .. versionadded:: 2.0
        """
        return cls(0x6DAE81)

    @classmethod
    def macaroni_and_cheese(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFBD88``.

        .. versionadded:: 2.0
        """
        return cls(0xFFBD88)

    @classmethod
    def atomic_tangerine(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFFA474``.

        .. versionadded:: 2.0
        """
        return cls(0xFFA474)

    @classmethod
    def maroon(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xC8385A``.

        .. versionadded:: 2.0
        """
        return cls(0xC8385A)

    @classmethod
    def antique_brass(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xCD9575``.

        .. versionadded:: 2.0
        """
        return cls(0xCD9575)

    @classmethod
    def timberwolf(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xDBD7D2``.

        .. versionadded:: 2.0
        """
        return cls(0xDBD7D2)

    @classmethod
    def outer_space(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x414A4C``.

        .. versionadded:: 2.0
        """
        return cls(0x414A4C)

    @classmethod
    def violet_purple(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x926EAE``.

        .. versionadded:: 2.0
        """
        return cls(0x926EAE)

    @classmethod
    def shadow(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0x8A795D``.

        .. versionadded:: 2.0
        """
        return cls(0x8A795D)

    @classmethod
    def radical_red(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFF496C``.

        .. versionadded:: 2.0
        """
        return cls(0xFF496C)

    @classmethod
    def burnt_sienna(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xEA7E5D``.

        .. versionadded:: 2.0
        """
        return cls(0xEA7E5D)

    @classmethod
    def mauvelous(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xEF98AA``.

        .. versionadded:: 2.0
        """
        return cls(0xEF98AA)

    @classmethod
    def pink_flamingo(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFC74FD``.

        .. versionadded:: 2.0
        """
        return cls(0xFC74FD)

    @classmethod
    def piggy_pink(cls: Type[CT]) -> CT:
        """A factory method that returns a :class:`Colour` with a value of ``0xFDDDE6``.

        .. versionadded:: 2.0
        """
        return cls(0xFDDDE6)

Color = Colour
Accent = Colour

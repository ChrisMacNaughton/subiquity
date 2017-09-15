# Copyright 2015 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from functools import partial

from urwid import AttrWrap, Button, connect_signal, Text

class PlainButton(Button):
    button_left = Text("")
    button_right = Text("")


class MenuSelectButton(Button):
    button_left = Text("")
    button_right = Text(">")


def plain_btn(label, color, on_press=None, user_arg=None):
    button = PlainButton(label=label)
    if on_press is not None:
        connect_signal(button, 'click', on_press, user_arg)
    return AttrWrap(button, color, color + ' focus')


start_btn = partial(plain_btn, label="Start", color="save_button")
save_btn = partial(plain_btn, label="Save", color="save_button")
finish_btn = partial(plain_btn, label="Finish", color="save_button")
ok_btn = partial(plain_btn, label="OK", color="save_button")
confirm_btn = partial(plain_btn, label="Confirm", color="save_button")
done_btn = partial(plain_btn, label="\nDone\n", color="save_button")
continue_btn = partial(plain_btn, label="Continue", color="save_button")

reset_btn = partial(plain_btn, label="Reset", color="reset_button")

cancel_btn = partial(plain_btn, label="\nCancel\n", color="cancel_button")
back_btn = partial(plain_btn, label="\nBack\n", color="cancel_button")

danger_btn = partial(plain_btn, color="danger_button")

def menu_btn(label, on_press=None, user_arg=None):
    button = MenuSelectButton(label=label)
    if on_press is not None:
        connect_signal(button, 'click', on_press, user_arg)
    return AttrWrap(button, 'menu_button', 'menu_button focus')

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

""" Filesystem

Provides storage device selection and additional storage
configuration.

"""
import logging

from urwid import connect_signal, Text, WidgetDisable

from subiquitycore.ui.buttons import delete_btn, menu_btn
from subiquitycore.ui.form import (
    Form,
    FormField,
    )
from subiquitycore.ui.interactive import StringEditor
from subiquitycore.ui.selector import Option, Selector
from subiquitycore.ui.container import Pile
from subiquitycore.ui.stretchy import Stretchy
from subiquitycore.ui.utils import Color, button_pile

from subiquity.models.filesystem import (
    align_up,
    FilesystemModel,
    HUMAN_UNITS,
    dehumanize_size,
    humanize_size,
    )
from subiquity.ui.mount import MountField


log = logging.getLogger('subiquity.ui.filesystem.add_partition')


class FSTypeField(FormField):
    def _make_widget(self, form):
        return Selector(opts=FilesystemModel.supported_filesystems)

class SizeWidget(StringEditor):
    def __init__(self, form):
        self.form = form
        super().__init__()

    def lost_focus(self):
        val = self.value
        if not val:
            return
        suffixes = ''.join(HUMAN_UNITS) + ''.join(HUMAN_UNITS).lower()
        if val[-1] not in suffixes:
            unit = self.form.size_str[-1]
            val += unit
            self.value = val
        try:
            sz = self.form.size.value
        except ValueError:
            return
        if sz > self.form.max_size:
            self.form.size.show_extra(('info_minor', _("Capped partition size at %s")%(self.form.size_str,)))
            self.value = self.form.size_str
        elif align_up(sz) != sz and humanize_size(align_up(sz)) != self.form.size.value:
            sz_str = humanize_size(align_up(sz))
            self.form.size.show_extra(('info_minor', _("Rounded size up to %s")%(sz_str,)))
            self.value = sz_str

class SizeField(FormField):
    def _make_widget(self, form):
        return SizeWidget(form)

class PartitionForm(Form):

    def __init__(self, mountpoint_to_devpath_mapping, max_size, initial={}):
        self.mountpoint_to_devpath_mapping = mountpoint_to_devpath_mapping
        self.max_size = max_size
        if max_size is not None:
            self.size_str = humanize_size(max_size)
            self.size.caption = _("Size (max {})").format(self.size_str)
        super().__init__(initial)
        if max_size is None:
            self.remove_field('size')
        connect_signal(self.fstype.widget, 'select', self.select_fstype)
        self.select_fstype(None, self.fstype.widget.value)

    def select_fstype(self, sender, fs):
        self.mount.enabled = fs.is_mounted

    size = SizeField()
    fstype = FSTypeField("Format")
    mount = MountField("Mount")

    def clean_size(self, val):
        if not val:
            return self.max_size
        suffixes = ''.join(HUMAN_UNITS) + ''.join(HUMAN_UNITS).lower()
        if val[-1] not in suffixes:
            val += self.size_str[-1]
        if val == self.size_str:
            return self.max_size
        else:
            return dehumanize_size(val)

    def clean_mount(self, val):
        if self.fstype.value.is_mounted:
            return val
        else:
            return None

    def validate_mount(self):
        mount = self.mount.value
        if mount is None:
            return
        # /usr/include/linux/limits.h:PATH_MAX
        if len(mount) > 4095:
            return _('Path exceeds PATH_MAX')
        dev = self.mountpoint_to_devpath_mapping.get(mount)
        if dev is not None:
            return _("%s is already mounted at %s")%(dev, mount)


class PartitionFormatView(Stretchy):

    title = _("Partition")

    def __init__(self, parent, size, existing, initial, back, focus_buttons=False):

        self.parent = parent
        mountpoint_to_devpath_mapping = self.model.get_mountpoint_to_devpath_mapping()
        if existing is not None:
            fs = existing.fs()
            if fs is not None:
                if getattr(existing, 'flag', None) != "boot":
                    initial['fstype'] = self.model.fs_by_name[fs.fstype]
                mount = fs.mount()
                if mount is not None:
                    initial['mount'] = mount.path
                    if mount.path in mountpoint_to_devpath_mapping:
                        del mountpoint_to_devpath_mapping[mount.path]
            else:
                initial['fstype'] = self.model.fs_by_name[None]
        self.form = PartitionForm(mountpoint_to_devpath_mapping, size, initial)

        connect_signal(self.form, 'submit', self.done)
        connect_signal(self.form, 'cancel', self.cancel)

        widgets = [
            Pile(self.form.as_rows()),
            Text(""),
            self.form.buttons,
            ]

        focus_index = 0
        if focus_buttons:
            focus_index = 2

        if existing:
            title = _("Partition")
        else:
            title = _("Add partition to {}".format(self.disk.label))

        super().__init__(title, widgets, 0, focus_index)

    def make_body(self):
        return self.form.as_rows()

    def cancel(self, button=None):
        self.parent.remove_overlay()


bios_grub_partition_description = _("""\
Required bootloader partition

GRUB will be installed onto the target disk's MBR.

However, on a disk with a GPT partition table, there is not enough space after the MBR for GRUB to store its second-stage core.img, so a small unformatted partition is needed at the start of the disk. It will not contain a filesystem and will not be mounted, and cannot be edited here.""")

boot_partition_description = _("""\
Required bootloader partition

This is the ESP / "EFI system partition" required by UEFI. Grub will be installed onto this partition, which must be formatted as fat32. The only aspect of this partition that can be edited is the size.""")


class PartitionView(PartitionFormatView):

    def __init__(self, parent, disk, partition=None):
        log.debug('PartitionView: selected_disk=[{}]'.format(disk.path))
        self.model = parent.model
        self.controller = parent.controller
        self.disk = disk
        self.partition = partition

        max_size = disk.free
        initial = {}
        if partition is None:
            label = _("Create")
        else:
            max_size += partition.size
            initial['size'] = humanize_size(partition.size)
            if partition.flag == "bios_grub":
                label = None
                initial['mount'] = None
            else:
                label = _("Save")
        super().__init__(parent, max_size, partition, initial, lambda : self.controller.partition_disk(disk), focus_buttons=label is None)
        if label is not None:
            self.form.buttons.base_widget[0].set_label(label)
        else:
            del self.form.buttons.base_widget.contents[0]
            self.form.buttons.base_widget[0].set_label(_("OK"))
        if partition is not None:
            if partition.flag == "boot":
                opts = [Option(("fat32", True, self.model.fs_by_name["fat32"]))]
                self.form.fstype.widget._options = opts
                self.form.fstype.widget.index = 0
                self.form.mount.enabled = False
                self.form.fstype.enabled = False
            elif partition.flag == "bios_grub":
                self.form.mount.enabled = False
                self.form.fstype.enabled = False
                self.form.size.enabled = False

    def make_body(self):
        body = super().make_body()
        if self.partition is not None:
            if self.partition.flag == "boot":
                body[0:0] = [
                    Text(_(boot_partition_description)),
                    Text(""),
                    ]
            elif self.partition.flag == "bios_grub":
                body[0:0] = [
                    Text(_(bios_grub_partition_description)),
                    Text(""),
                    ]
            btn = delete_btn(_("Delete"), on_press=self.delete)
            if self.partition.flag == "boot" or self.partition.flag == "bios_grub":
                btn = WidgetDisable(Color.info_minor(btn.original_widget))
            body.extend([
                Text(""),
                button_pile([btn]),
                ])
        return body

    def delete(self, sender):
        self.controller.delete_partition(self.partition)

    def done(self, form):
        log.debug("Add Partition Result: {}".format(form.as_data()))
        self.controller.partition_disk_handler(self.disk, self.partition, form.as_data())


class AddPartitionStretchy(Stretchy):

    def __init__(self, parent, dev):

        self.disk = dev
        self.model = parent.model
        self.controller = parent.controller
        self.parent = parent
        max_size = dev.size
        mountpoint_to_devpath_mapping = self.model.get_mountpoint_to_devpath_mapping()
        self.form = PartitionForm(mountpoint_to_devpath_mapping, max_size, {})

        connect_signal(self.form, 'submit', self.done)
        connect_signal(self.form, 'cancel', self.cancel)

        rows = self.form.as_rows()
        rows.extend([
            Text(""),
            button_pile([menu_btn("Show disk info")]),
            ])
        widgets = [
            Pile(rows),
            Text(""),
            self.form.buttons,
            ]

        title = _("Adding partition to {}").format(self.disk.label)

        super().__init__(title, widgets, 0, 0)

    def cancel(self, button=None):
        self.parent.remove_overlay()

    def done(self, form):
        log.debug("Add Partition Result: {}".format(form.as_data()))
        self.controller.partition_disk_handler(self.disk, None, form.as_data())

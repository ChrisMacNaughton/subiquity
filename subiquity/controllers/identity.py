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

import logging

from subiquitycore.controller import BaseController
from subiquitycore import utils

from subiquity.ui.views import IdentityView

log = logging.getLogger('subiquity.controllers.identity')


class FetchSSHKeysFailure(Exception):
    def __init__(self, message, output):
        self.message = message
        self.output = output


class IdentityController(BaseController):

    def __init__(self, common):
        super().__init__(common)
        self.model = self.base_model.identity
        self.answers = self.all_answers.get('Identity', {})

    def default(self):
        self.ui.set_body(IdentityView(self.model, self, self.opts))
        if all(elem in self.answers for elem in
               ['realname', 'username', 'password', 'hostname']):
            d = {
                'realname': self.answers['realname'],
                'username': self.answers['username'],
                'hostname': self.answers['hostname'],
                'password': self.answers['password'],
                }
            if 'ssh_import_id' in self.answers:
                ssh_import_id = self.answers['ssh_import_id']
                self.fetch_ssh_keys(d, ssh_import_id)
            else:
                self.done(d)

    def cancel(self):
        self.signal.emit_signal('prev-screen')

    def _fetch_cancel(self):
        if self._fetching_proc is None:
            return
        try:
            self._fetching_proc.terminate()
        except ProcessLookupError:
            pass  # It's OK if the process has already terminated.
        self._fetching_proc = None

    def _bg_fetch_ssh_keys(self, user_spec, proc, ssh_import_id):
        stdout, stderr = proc.communicate()
        stdout = stdout.decode('utf-8', errors='replace')
        stderr = stderr.decode('utf-8', errors='replace')
        log.debug("ssh-import-id exited with code %s", proc.returncode)
        if proc != self._fetching_proc:
            log.debug("_fetch_ssh_keys cancelled")
            return None
        if proc.returncode != 0:
            raise FetchSSHKeysFailure(_("Importing keys failed:"), stderr)
        key_material = stdout.replace('\r', '').strip()

        cp = utils.run_command(['ssh-keygen', '-lf-'], input=key_material)
        if cp.returncode != 0:
            return FetchSSHKeysFailure(_("ssh-keygen failed to show "
                                         "fingerprint of downloaded keys:"),
                                       cp.stderr)
        fingerprints = (
            cp.stdout.replace("# ssh-import-id {} ".format(ssh_import_id),
                              "").strip().splitlines())

        return user_spec, key_material, fingerprints

    def _fetched_ssh_keys(self, fut):
        try:
            result = fut.result()
        except FetchSSHKeysFailure as e:
            log.debug("fetching ssh keys failed %s", e)
            self.ui.frame.body.fetching_ssh_keys_failed(e.message, e.output)
        else:
            log.debug("_fetched_ssh_keys %s", result)
            if result is None:
                # Happens if the fetch is cancelled.
                return
            user_spec, key_material, fingerprints = result
            if 'ssh_import_id' in self.answers:
                user_spec['ssh_keys'] = key_material.splitlines()
                self.loop.set_alarm_in(0.0,
                                       lambda loop, ud: self.done(user_spec))
            else:
                self.ui.frame.body.confirm_ssh_keys(user_spec, key_material,
                                                    fingerprints)

    def fetch_ssh_keys(self, user_spec, ssh_import_id):
        log.debug("User input: %s, fetching ssh keys for %s",
                  user_spec, ssh_import_id)
        self._fetching_proc = utils.start_command(['ssh-import-id', '-o-',
                                                   ssh_import_id])
        self.run_in_bg(
            lambda: self._bg_fetch_ssh_keys(user_spec, self._fetching_proc,
                                            ssh_import_id),
            self._fetched_ssh_keys)

    def done(self, user_spec):
        log.debug("User input: {}".format(user_spec))
        self.model.add_user(user_spec)
        self.signal.emit_signal('installprogress:identity-config-done')
        self.signal.emit_signal('next-screen')

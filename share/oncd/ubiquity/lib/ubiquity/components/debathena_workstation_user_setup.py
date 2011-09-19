# -*- coding: utf-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Xavid <xavid@mit.edu> based on code by
# Colin Watson <cjwatson@ubuntu.com>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from ubiquity.components import usersetup

NAME='usersetup'

class Page(usersetup.Page):
    def prepare(self):
        cmd,questions = usersetup.Page.prepare(self)
        questions.append('^passwd/root-login$')
        questions.append('^passwd/root-password$')
        questions.append('^passwd/root-password-again$')
        questions.append('^passwd/make-user$')
        return (cmd,questions)
    def ok_handler(self):
        self.preseed_bool('passwd/root-login', True)
        self.preseed('passwd/root-password', self.frontend.get_password())
        self.preseed('passwd/root-password-again', 
                     self.frontend.get_verified_password())
        # Don't actually create user -- this only works if root-login is True
        # Otherwise you need to do it after user-setup-ask is done
        self.preseed_bool('passwd/make-user', False)
        
        usersetup.Page.ok_handler(self)
        
        new = '; '.join(("for group in %s sudo admin",
                         "do chroot /target /usr/sbin/adduser '%s' $group",
                         "done",
                         "echo 'root:%s' | chroot /target /usr/sbin/chpasswd",
                         "sed -ri 's/AllowRoot=\w+/AllowRoot=true/' /target/etc/gdm/gdm.conf",
                         "echo '%%sudo ALL=(ALL) ALL' >> /target/etc/sudoers"
                         )) % (
                self.db.get('passwd/user-default-groups'), 
                self.db.get('passwd/username'),
                self.frontend.get_password().replace("'",
                                                     """'"'"'""")
                )
        self.frontend.success_cmd = new+'; '+self.frontend.success_cmd



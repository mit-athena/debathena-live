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

import copy

from ubiquity.plugin import *

from ubiquity.components import usersetup, debathena_workstation_user_setup

NAME = 'debathena'
AFTER = None
WEIGHT = 1

class stash(object):
    pass

dead_for_workstation = ['fullname_label','fullname','fullname_error_box',
                        'auto_login','login_pass','login_auto','login_vbox']
markup_for_workstation = {'username_label':
                          "What's your Athena username?",
                          'username_extra_label':
                          "<i>You will be an adminstrator on this computer; you can add other adminstrators after installation.</i>",
                          'password_label':"Choose a root password for this workstation.",
                          'password_extra_label':"<i>Enter the same password twice.  You can log in as root to fix network problems that prevent you from logging in normally.</i>"}

originals = None

class PageGtk(PluginUI):
    def __init__(self, controller, *args, **kw):
        self.controller = controller
        import gtk
        builder = gtk.Builder()
        builder.add_from_file('/usr/share/ubiquity/gtk/stepDebathenaType.ui')
        builder.connect_signals(self)
        self.page = builder.get_object('stepDebathenaType')
        self.debathena_workstation = builder.get_object('debathena_workstation')
        self.debathena_standard = builder.get_object('debathena_standard')
        self.plugin_widgets = self.page

    def get_debathena_type(self):
        for b in self.debathena_workstation.get_group():
            if b.get_active():
                return b.get_name()
    def set_debathena_type(self,typ):
        if not typ.startswith('debathena_') or not hasattr(self,typ):
            self.error_dialog('Debathena Error',
                              "Debathena type '%s' is illegal!" % typ)
        getattr(self,typ).set_active(True)



class Page(Plugin):
    def prepare(self,unfiltered=False):
        questions = ['^debathena/type$']
        return ('/usr/share/ubiquity/debathena',
                questions)

    def ok_handler(self):
        global originals, dead_for_workstation
        typ = self.ui.get_debathena_type()

        if originals is None:

            # Patch originals (i.e., debathena-standard)
            self.frontend.username_label.set_text(
                self.frontend.username_label.get_text()+"  (You may wish to use your Athena username.)")

            originals = stash()
            dead_for_workstation = [d for d in dead_for_workstation
                                    if hasattr(self.frontend,d)]
            
            new = 'rm -Rf /target/oncd ; chroot /target /usr/bin/aptitude remove -y casper'
            if self.frontend.success_cmd:
                originals.success_cmd = self.frontend.success_cmd+'; '+new
            else:
                originals.success_cmd = new

            for i in xrange(len(self.frontend.modules)):
                if self.frontend.modules[i].module == usersetup:
                    originals.usersetup_index = i
                    break
            else:
                raise Exception("page not found")

            originals.usersetup = self.frontend.modules[originals.usersetup_index].filter_class
            originals.size_requests = dict((d,
                                                 getattr(self.frontend,d)
                                                 .get_size_request())
                                                for d in dead_for_workstation)
            originals.markups = dict((m,
                                           getattr(self.frontend,m)
                                           .get_text())
                                          for m in markup_for_workstation)

        # Preseed for debathena
        self.preseed_bool('apt-setup/universe',True)

        if typ == 'debathena_workstation':
            # Modify user creation screen
            # -! this only handles the gtk_ui, much like this whole process
            self.frontend.modules[originals.usersetup_index].filter_class = debathena_workstation_user_setup.Page
            for d in dead_for_workstation:
                w = getattr(self.frontend,d)
                w.hide()
                w.set_size_request(0,0)
            for m in markup_for_workstation:
                w = getattr(self.frontend,m)
                w.set_markup(markup_for_workstation[m])

            # Also, install debathena-workstation instead of our current
            # debathena-login-graphical (we've got the .debs cached)
            new = "cp /usr/share/ubiquity/policy-rc.d /target/usr/sbin/ && mount --rbind /dev /target/dev && echo 'sun-java6-bin shared/accepted-sun-dlj-v1-1 boolean true' | chroot /target debconf-set-selections && chroot /target /usr/bin/xterm -e 'env DEBCONF_NONINTERACTIVE_SEEN=true DEBIAN_FRONTEND=noninteractive debconf-apt-progress -- aptitude install -y debathena-workstation' && rm /target/usr/sbin/policy-rc.d"
            self.frontend.success_cmd = new+'; '+originals.success_cmd

        elif typ == 'debathena_standard':
            # Undo changes debathena_workstation might have made,
            # since we could have backtracked
            self.frontend.modules[originals.usersetup_index].filter_class = originals.usersetup
            for d in dead_for_workstation:
                w = getattr(self.frontend,d)
                if 'error' not in d:
                    w.show()
                w.set_size_request(*originals.size_requests[d])
            for m in markup_for_workstation:
                w = getattr(self.frontend,m)
                w.set_text(originals.markups[m])
            
            # Use normal user creation screen, use this magic command
            # to switch to debathena-standard while purging 
            # debathena-workstation
            # (I don't think this actually purges its dependencies, though,
            #  just removes them.)
            new = """cp /usr/share/ubiquity/policy-rc.d /target/usr/sbin/ && mount --rbind /dev /target/dev && chroot /target /usr/bin/xterm -e "debconf-apt-progress -- aptitude install -y 'debathena-standard&m' 'debathena-login-graphical_'" && rm /target/usr/sbin/policy-rc.d"""
            self.frontend.success_cmd = new+'; '+originals.success_cmd
        else:
            assert False, typ

        FilteredCommand.ok_handler(self)


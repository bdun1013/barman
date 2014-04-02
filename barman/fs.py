# Copyright (C) 2013-2014 2ndQuadrant Italia (Devise.IT S.r.L.)
#
# This file is part of Barman.
#
# Barman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Barman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Barman.  If not, see <http://www.gnu.org/licenses/>.

import logging
from barman.command_wrappers import Command
from shutil import rmtree

_logger = logging.getLogger(__name__)


class FsOperationFailed(Exception):
    """
    Exception which represents a failed execution of a command on FS
    """
    pass


class UnixLocalCommand(object):
    """
    This class is a wrapper for local calls for file system operations
    """

    def __init__(self):
        # initialize a shell
        self.cmd = Command(cmd='sh -c', shell=True)

    def create_dir_if_not_exists(self, dir_path):
        """
            This method check for the existence of a directory.
            if exist and is not a directory throws exception.
            if is a directory everything is ok and no
            mkdir operation is required.
            Otherwise creates the directory using mkdir
            if the mkdir fails an error is raised

            :param dir_path full path for the directory
        """
        _logger.debug('Create directory %s if it does not exists' % dir_path)
        exists = self.cmd('test -e %s' % dir_path)
        if exists == 0:
            is_dir = self.cmd('test -d %s' % dir_path)
            if is_dir != 0:
                raise FsOperationFailed(
                    'A file with the same name already exists')
            else:
                return False
        else:
            mkdir_ret = self.cmd('mkdir %s' % dir_path)
            if mkdir_ret == 0:
                return True
            else:
                raise FsOperationFailed('mkdir execution failed')

    def delete_if_exists(self, dir_path):
        """
            This method check for the existence of a directory.
            if exists and is not a directory an exception is raised
            if is a directory, then is removed using a rm -fr command,
            and returns True.
            if the command fails an exception is raised.
            If the directory does not exists returns False

            :param dir_path the full path for the directory
        """
        _logger.debug('Delete if directory %s exists' % dir_path)
        exists = self.cmd('test -e %s' % dir_path)
        if exists == 0:
            is_dir = self.cmd('test -d %s' % dir_path)
            if is_dir != 0:
                raise FsOperationFailed(
                    'A file with the same name exists, but is not a '
                    'directory')
            else:
                rm_ret = self.cmd('rm -fr %s' % dir_path)
                if rm_ret == 0:
                    return True
                else:
                    raise FsOperationFailed('rm execution failed')
        else:
            return False

    def check_directory_exists(self, dir_path):
        """
            Check for the existence of a directory in path.
            if the directory exists returns true.
            if the directory does not exists returns false.
            if exists a file and is not a directory raises an exception

            :param dir_path full path for the directory
        """
        _logger.debug('Check if directory %s exists' % dir_path)
        exists = self.cmd('test -e %s' % dir_path)
        if exists == 0:
            is_dir = self.cmd('test -d %s' % dir_path)
            if is_dir != 0:
                raise FsOperationFailed(
                    'A file with the same name exists, but is not a directory')
            else:
                return True
        else:
            return False

    def check_write_permission(self, dir_path):
        """
            check write permission for barman on a given path.
            Creates a hidden file using touch, then remove the file.
            returns true if the file is written and removed without problems
            raise exception if the creation fails.
            raise exception if the removal fails.

            :param dir_path full dir_path for the directory to check
        """
        _logger.debug('Check if directory %s is writable' % dir_path)
        exists = self.cmd('test -e %s' % dir_path)
        if exists == 0:
            is_dir = self.cmd('test -d %s' % dir_path)
            if is_dir == 0:
                can_write = self.cmd('touch %s/.barman_write_check' % dir_path)
                if can_write == 0:
                    can_remove = self.cmd(
                        'rm %s/.barman_write_check' % dir_path)
                    if can_remove == 0:
                        return True
                    else:
                        raise FsOperationFailed('Unable to remove file')
                else:
                    raise FsOperationFailed('Unable to create write check file')
            else:
                raise FsOperationFailed('%s is not a directory' % dir_path)
        else:
            raise FsOperationFailed('%s does not exists' % dir_path)

    def create_symbolic_link(self, src, dst):
        """
            Create a symlink pointing to src named dst.
            Check src exists, if so, checks that destination
            does not exists. if src is an invalid folder, raises an exception.
            if dst allready exists, raises an exception. if ln -s command fails
            raises an exception

            :param src full path to the source of the symlink
            :param dst full path for the destination of the symlink
        """
        _logger.debug('Create symbolic link %s -> %s' % (src, dst))
        exists = self.cmd('test -e %s' % src)
        if exists == 0:
            exists_dst = self.cmd('test -e %s' % dst)
            if exists_dst != 0:
                link = self.cmd('ln -s %s %s' % (src, dst))
                if link == 0:
                    return True
                else:
                    raise FsOperationFailed('ln command failed')
            else:
                raise FsOperationFailed('ln destination already exists')
        else:
            raise FsOperationFailed('ln source does not exists')

    def get_system_info(self):
        """
            Gather important system information for 'barman diagnose' command
        """
        result = {}
        lsb_return = self.cmd("lsb_release -a")
        lsb = ''
        if lsb_return == 0:
            lsb = self.cmd.out.rstrip()
        elif self.cmd('test -e /etc/lsb-release') == 0:
            self.cmd('cat /etc/lsb-release ')
            lsb = "Ubuntu Linux %s" % self.cmd.out.rstrip()
        elif self.cmd('test -e /etc/lsb-release') == 0:
            self.cmd('cat /etc/debian_version')
            lsb = "Debian GNU/Linux %s" % self.cmd.out.rstrip()
        elif self.cmd('test -e /etc/lsb-release') == 0:
            self.cmd('cat /etc/redhat-release')
            lsb = "RedHat Linux %s" % self.cmd.out.rstrip()

        self.cmd('uname -a')
        result['kernel_ver'] = self.cmd.out.rstrip()
        r = self.cmd('python --version 2>&1')
        result['python_ver'] = self.cmd.out.rstrip()
        r = self.cmd('rsync --version 2>&1')
        result['rsync_ver'] = str(self.cmd.out).splitlines(True)[0].rstrip()
        r = self.cmd('ssh -v 2>&1')
        result['ssh_ver'] = str(self.cmd.out).splitlines(True)[0].rstrip()
        return result


class UnixRemoteCommand(UnixLocalCommand):
    """
    This class is a wrapper for remote calls for file system operations
    """

    # noinspection PyMissingConstructor
    def __init__(self, ssh_command):
        """
            Uses the same commands as the UnixLocalCommand
            but the constructor is overridden and a remote shell is
            initialized using the ssh_command provided by the user

            :param ssh_command the ssh command provided by the user
        """
        if ssh_command is None:
            raise FsOperationFailed('No ssh command provided')
        self.cmd = Command(cmd=ssh_command, shell=True)
        ret = self.cmd("true")
        if ret != 0:
            raise FsOperationFailed("Connection failed using the command '%s'" %
                                    ssh_command)
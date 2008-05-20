# -*- coding: iso-8859-1 -*-
# Copyright (C) 2000-2008 Bastian Kleineidam
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
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""
Output logging support for different formats.
"""

import sys
import os
import datetime
from ..decorators import notimplemented
from .. import log, LOG_CHECK, strformat, i18n, dummy

_ = lambda x: x
Fields = dict(
    realurl=_("Real URL"),
    cachekey=_("Cache key"),
    result=_("Result"),
    base=_("Base"),
    name=_("Name"),
    parenturl=_("Parent URL"),
    extern=_("Extern"),
    info=_("Info"),
    warning=_("Warning"),
    dltime=_("D/L Time"),
    dlsize=_("D/L Size"),
    checktime=_("Check Time"),
    url=_("URL"),
)
del _

class Logger (object):
    """
    Basic logger class enabling logging of checked urls.
    """

    def __init__ (self, **args):
        """
        Initialize a logger, looking for part restrictions in kwargs.
        """
        # what log parts should be in output
        self.logparts = None # log all parts
        if 'parts' in args:
            if "all" not in args['parts']:
                # only log given parts
                self.logparts = args['parts']
        # number of spaces before log parts for alignment
        self.logspaces = {}
        # maximum indent of spaces for alignment
        self.max_indent = 0
        # number of logged urls
        self.number = 0
        # number of encountered errors
        self.errors = 0
        # number of errors that were printed
        self.errors_printed = 0
        # number of warnings
        self.warnings = 0
        # number of warnings that were printed
        self.warnings_printed = 0
        # encoding of output
        self.output_encoding = args.get("encoding", i18n.default_encoding)

    def init_fileoutput (self, args):
        """
        Initialize self.fd file descriptor from args.
        """
        self.filename = None
        self.close_fd = False
        self.fd = None
        if args.get('fileoutput'):
            self.filename = os.path.expanduser(args['filename'])
        elif 'fd' in args:
            self.fd = args['fd']
        else:
            self.fd = sys.stdout

    def start_fileoutput (self):
        path = os.path.dirname(self.filename)
        try:
            if path and not os.path.isdir(path):
                os.makedirs(path)
            self.fd = file(self.filename, "wb")
            self.close_fd = True
        except IOError:
            msg = sys.exc_info()[1]
            log.warn(LOG_CHECK,
                "Could not open file %r for writing: %s\n"
                "Disabling log output of %s", self.filename, msg, self)
            self.fd = dummy.Dummy()
        self.filename = None

    def close_fileoutput (self):
        """
        Flush and close the file output denoted by self.fd.
        """
        if self.fd is not None:
            self.flush()
            if self.close_fd:
                self.fd.close()
            self.fd = None

    def encode (self, s):
        """
        Encode string with configured output encoding. Wrong encoded
        characters are replaced.

        @param s: string to encode
        @type s: unicode
        @return: encoded string
        @rtype: string
        """
        if not isinstance(s, unicode):
            raise ValueError("tried to encode non-unicode string %r" % s)
        return s.encode(self.output_encoding, "replace")

    def decode (self, s):
        """
        Decode string with configured output encoding. Wrong decoded
        characters are replaced.

        @param s: string to decode
        @type s: string
        @return: encoded string
        @rtype: unicode
        """
        if isinstance(s, unicode):
            return s
        return s.decode(self.output_encoding, "replace")

    def check_date (self):
        """
        Check for special dates.
        """
        now = datetime.date.today()
        if now.day == 7 and now.month == 1:
            msg = _("Happy birthday for LinkChecker, I'm %d years old today!")
            self.comment(msg % (now.year - 2000))

    def comment (self, s, **args):
        """
        Write a comment and a newline. This method just prints
        the given string.
        """
        self.writeln(s=s, **args)

    def wrap (self, lines, width):
        """
        Return wrapped version of given lines.
        """
        sep = os.linesep+os.linesep
        text = sep.join(lines)
        return strformat.wrap(text, width,
                            subsequent_indent=" "*self.max_indent,
                            initial_indent=" "*self.max_indent).lstrip()

    def write (self, s, **args):
        """
        Write string to output descriptor.
        """
        if self.filename is not None:
            self.start_fileoutput()
        if self.fd is None:
            # Happens when aborting threads times out
            log.warn(LOG_CHECK,
                "writing to unitialized or closed file")
        else:
            self.fd.write(self.encode(s), **args)

    def writeln (self, s=u"", **args):
        """
        Write string to output descriptor plus a newline.
        """
        self.write(s)
        self.write(unicode(os.linesep), **args)

    def has_part (self, name):
        """
        See if given part name will be logged.
        """
        if self.logparts is None:
            # log all parts
            return True
        return name in self.logparts

    def part (self, name):
        """
        Return translated part name.
        """
        return _(Fields[name])

    def spaces (self, name):
        """
        Return indent of spaces for given part name.
        """
        return self.logspaces[name]

    def start_output (self):
        """
        Start log output.
        """
        # map with spaces between part name and value
        if self.logparts is None:
            parts = Fields.keys()
        else:
            parts = self.logparts
        values = (self.part(x) for x in parts)
        # maximum indent for localized log part names
        self.max_indent = max(len(x) for x in values)+1
        for key in parts:
            numspaces = (self.max_indent - len(self.part(key)))
            self.logspaces[key] = u" " * numspaces

    def log_filter_url (self, url_data, do_print):
        """
        Log a new url with this logger if do_filter is True. Else
        only update accounting data
        """
        self.number += 1
        if not url_data.valid:
            self.errors += 1
            if do_print:
                self.errors_printed += 1
        num_warnings = len(url_data.warnings)
        self.warnings += num_warnings
        if do_print:
            self.warnings_printed += num_warnings
            self.log_url(url_data)

    @notimplemented
    def log_url (self, url_data):
        """
        Log a new url with this logger.
        """
        pass

    @notimplemented
    def end_output (self):
        """
        End of output, used for cleanup (eg output buffer flushing).
        """
        pass

    def __str__ (self):
        """
        Return class name.
        """
        return self.__class__.__name__

    def __repr__ (self):
        """
        Return class name.
        """
        return repr(self.__class__.__name__)

    def flush (self):
        """
        If the logger has internal buffers, flush them.
        Ignore flush I/O errors since we are not responsible for proper
        flushing of log output streams.
        """
        if hasattr(self, "fd"):
            try:
                self.fd.flush()
            except (IOError, AttributeError):
                pass

# note: don't confuse URL loggers with application logs above
from .text import TextLogger
from .html import HtmlLogger
from .gml import GMLLogger
from .dot import DOTLogger
from .sql import SQLLogger
from .csvlog import CSVLogger
from .blacklist import BlacklistLogger
from .gxml import GraphXMLLogger
from .customxml import CustomXMLLogger
from .none import NoneLogger


# default link logger classes
Loggers = {
    "text": TextLogger,
    "html": HtmlLogger,
    "gml": GMLLogger,
    "dot": DOTLogger,
    "sql": SQLLogger,
    "csv": CSVLogger,
    "blacklist": BlacklistLogger,
    "gxml": GraphXMLLogger,
    "xml": CustomXMLLogger,
    "none": NoneLogger,
}
# for easy printing: a comma separated logger list
LoggerKeys = ", ".join(repr(name) for name in Loggers)



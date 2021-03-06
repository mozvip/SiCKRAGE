# Author: echel0n <echel0n@sickrage.ca>
# URL: https://sickrage.ca
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import logging
import os
import pkgutil
import re
from logging import FileHandler, CRITICAL, DEBUG, ERROR, INFO, WARNING
from logging.handlers import RotatingFileHandler

from unidecode import unidecode

import sickrage
from sickrage.core import makeDir


class srLogger(logging.getLoggerClass()):
    logging.captureWarnings(True)
    logging.getLogger().addHandler(logging.NullHandler())

    def __init__(self, name="sickrage"):
        super(srLogger, self).__init__(name)
        self.propagate = False

        self.consoleLogging = True
        self.fileLogging = False
        self.debugLogging = False

        self.logFile = None
        self.logSize = 1048576
        self.logNr = 5

        self.CRITICAL = CRITICAL
        self.DEBUG = DEBUG
        self.ERROR = ERROR
        self.WARNING = WARNING
        self.INFO = INFO
        self.DB = 5

        self.CENSORED_ITEMS = {}

        self.logLevels = {
            'CRITICAL': self.CRITICAL,
            'ERROR': self.ERROR,
            'WARNING': self.WARNING,
            'INFO': self.INFO,
            'DEBUG': self.DEBUG,
            'DB': 5
        }

        # list of allowed loggers
        self.loggers = {'sickrage': self,
                        'tornado.general': logging.getLogger('tornado.general'),
                        'tornado.application': logging.getLogger('tornado.application'),
                        'apscheduler.jobstores': logging.getLogger('apscheduler.jobstores'),
                        'apscheduler.scheduler': logging.getLogger('apscheduler.scheduler')}

        # set custom level for database logging
        logging.addLevelName(self.logLevels['DB'], 'DB')
        self.setLevel(self.logLevels['DB'])

        # start logger
        self.start()

    def start(self):
        # remove all handlers
        self.handlers = []

        # console log handler
        if self.consoleLogging:
            console = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(levelname)s::%(threadName)s::%(message)s', '%H:%M:%S')

            console.setFormatter(formatter)
            console.setLevel(self.logLevels['INFO'] if not self.debugLogging else self.logLevels['DEBUG'])
            self.addHandler(console)

        # file log handlers
        if self.logFile and makeDir(os.path.dirname(self.logFile)):
            if sickrage.srCore.srConfig.DEVELOPER:
                rfh = FileHandler(
                    filename=self.logFile,
                )
            else:
                rfh = RotatingFileHandler(
                    filename=self.logFile,
                    maxBytes=self.logSize,
                    backupCount=self.logNr
                )

            rfh_errors = RotatingFileHandler(
                filename=self.logFile.replace('.log', '.error.log'),
                maxBytes=self.logSize,
                backupCount=self.logNr
            )

            formatter = logging.Formatter('%(asctime)s %(levelname)s::%(threadName)s::%(message)s', '%Y-%m-%d %H:%M:%S')

            rfh.setFormatter(formatter)
            rfh.setLevel(self.logLevels['INFO'] if not self.debugLogging else self.logLevels['DEBUG'])
            self.addHandler(rfh)

            rfh_errors.setFormatter(formatter)
            rfh_errors.setLevel(self.logLevels['ERROR'])
            self.addHandler(rfh_errors)

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
        if (False, True)[name in self.loggers]:
            record = super(srLogger, self).makeRecord(name, level, fn, lno, msg, args, exc_info, func, extra)

            try:
                record.msg = re.sub(
                    r"(.*)\b({})\b(.*)".format(
                        '|'.join([x for x in self.CENSORED_ITEMS.values() if len(x)])), r"\1\3",
                    record.msg)

                # needed because Newznab apikey isn't stored as key=value in a section.
                record.msg = re.sub(r"([&?]r|[&?]apikey|[&?]api_key)=[^&]*([&\w]?)", r"\1=**********\2", record.msg)
                record.msg = unidecode(record.msg)
            except:
                pass

            # sending record to UI
            if record.levelno in [WARNING, ERROR]:
                from sickrage.core.classes import WarningViewer
                from sickrage.core.classes import ErrorViewer
                (WarningViewer(), ErrorViewer())[record.levelno == ERROR].add(record.msg, True)

            return record

    def set_level(self):
        self.debugLogging = sickrage.srCore.srConfig.DEBUG
        level = DEBUG if self.debugLogging else INFO
        for __, logger in self.loggers.items():
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)

    def list_modules(self, package):
        """Return all sub-modules for the specified package.

        :param package:
        :type package: module
        :return:
        :rtype: list of str
        """
        return [modname for importer, modname, ispkg in pkgutil.walk_packages(
            path=package.__path__, prefix=package.__name__ + '.', onerror=lambda x: None)]

    def get_loggers(self, package):
        """Return all loggers for package and sub-packages.

        :param package:
        :type package: module
        :return:
        :rtype: list of logging.Logger
        """
        return [logging.getLogger(modname) for modname in self.list_modules(package)]

    def log(self, level, msg, *args, **kwargs):
        super(srLogger, self).log(level, msg, *args, **kwargs)

    def db(self, msg, *args, **kwargs):
        super(srLogger, self).log(self.logLevels['DB'], msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        super(srLogger, self).info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        super(srLogger, self).debug(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        super(srLogger, self).critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        super(srLogger, self).exception(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        super(srLogger, self).error(msg, exc_info=1, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        super(srLogger, self).warning(msg, *args, **kwargs)

    def close(self, *args, **kwargs):
        logging.shutdown()

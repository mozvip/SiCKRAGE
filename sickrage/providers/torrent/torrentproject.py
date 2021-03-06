# coding=utf-8
# Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
#
# URL: https://sickrage.ca
#
# This file is part of SiCKRAGE.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SiCKRAGE. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, unicode_literals

import sickrage
from sickrage.core.caches.tv_cache import TVCache
from sickrage.core.helpers import validate_url, try_int, convert_size
from sickrage.providers import TorrentProvider


class TorrentProjectProvider(TorrentProvider):
    def __init__(self):
        super(TorrentProjectProvider, self).__init__('TorrentProject', 'https://torrentproject.se', False)

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        self.custom_url = ""

        # Cache
        self.cache = TVCache(self, search_params={'RSS': ['0day']})

    def search(self, search_strings, age=0, ep_obj=None):
        results = []

        search_params = {
            'out': 'json',
            'filter': 2101,
            'showmagnets': 'on',
            'num': 50
        }

        for mode in search_strings:
            sickrage.srCore.srLogger.debug("Search Mode: {0}".format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    sickrage.srCore.srLogger.debug("Search string: {0}".format
                                                   (search_string))

                search_params['s'] = search_string

                search_url = self.urls['base_url']
                if self.custom_url:
                    if not validate_url(self.custom_url):
                        sickrage.srCore.srLogger.warning("Invalid custom url set, please check your settings")
                        return results
                    search_url = self.custom_url

                try:
                    data = sickrage.srCore.srWebSession.get(search_url, params=search_params).json()
                    results += self.parse(data, mode)
                except Exception:
                    sickrage.srCore.srLogger.debug("No data returned from provider")

        return results

    def parse(self, data, mode):
        """
        Parse search results from data
        :param data: response data
        :param mode: search mode
        :return: search results
        """

        results = []

        if not (data and "total_found" in data and int(data["total_found"]) > 0):
            sickrage.srCore.srLogger.debug("Data returned from provider does not contain any torrents")
            return results

        del data["total_found"]

        for i in data:
            try:
                title = data[i]["title"]
                seeders = try_int(data[i]["seeds"], 1)
                leechers = try_int(data[i]["leechs"], 0)
                t_hash = data[i]["torrent_hash"]
                torrent_size = data[i]["torrent_size"]
                if not all([t_hash, torrent_size]):
                    continue

                download_url = data[i]["magnet"]
                size = convert_size(torrent_size, -1)

                if not all([title, download_url]):
                    continue

                item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders,
                        'leechers': leechers, 'hash': t_hash}

                if mode != 'RSS':
                    sickrage.srCore.srLogger.debug("Found result: {}".format(title))

                results.append(item)
            except Exception:
                sickrage.srCore.srLogger.error("Failed parsing provider.")

        return results
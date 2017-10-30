# Author: echel0n <echel0n@sickrage.ca>
# URL: https://sickrage.ca
# Git: https://git.sickrage.ca/SiCKRAGE/sickrage
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

from urlparse import urljoin

import sickrage
from sickrage.core.caches.tv_cache import TVCache
from sickrage.core.helpers import try_int, convert_size, validate_url
from sickrage.providers import TorrentProvider


class BitCannonProvider(TorrentProvider):
    def __init__(self):
        super(BitCannonProvider, self).__init__("BitCannon", 'http://localhost:3000', False)
        self.api_key = None

        self.minseed = None
        self.minleech = None

        self.custom_url = ""

        self.urls.update({
            'search': '{base_url}/api/search'.format(**self.urls)
        })

        self.cache = TVCache(self, search_params={'RSS': ['tv', 'anime']})

    def search(self, search_strings, age=0, ep_obj=None):
        results = []

        search_url = self.urls["search"]
        if self.custom_url:
            if not validate_url(self.custom_url):
                sickrage.srCore.srLogger.warning("Invalid custom url: {0}".format(self.custom_url))
                return results
            search_url = urljoin(self.custom_url, search_url.split(self.urls['base_url'])[1])

        # Search Params
        search_params = {
            'category': 'anime' if ep_obj and ep_obj.series and ep_obj.series.anime else 'tv',
            'apiKey': self.api_key,
        }

        for mode in search_strings:
            sickrage.srCore.srLogger.debug('Search mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                search_params['q'] = search_string
                if mode != 'RSS':
                    sickrage.srCore.srLogger.debug('Search string: {}'.format(search_string))

                response = sickrage.srCore.srWebSession.get(search_url, params=search_params)
                if not response or not response.content:
                    sickrage.srCore.srLogger.debug('No data returned from provider')
                    continue

                try:
                    jdata = response.json()
                except ValueError:
                    sickrage.srCore.srLogger.debug('No data returned from provider')
                    continue

                if not self._check_auth_from_data(jdata):
                    return results

                results += self.parse(jdata, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []
        torrent_rows = data.pop('torrents', {})

        # Skip column headers
        for row in torrent_rows:
            try:
                title = row.pop('title', '')
                info_hash = row.pop('infoHash', '')
                download_url = 'magnet:?xt=urn:btih:' + info_hash
                if not all([title, download_url, info_hash]):
                    continue

                swarm = row.pop('swarm', {})
                seeders = try_int(swarm.pop('seeders', 0))
                leechers = try_int(swarm.pop('leechers', 0))

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        sickrage.srCore.srLogger.debug("Discarding torrent because it doesn't meet the minimum  "
                                                       "seeders: {0}. Seeders: {1}".format(title, seeders))
                    continue

                size = convert_size(row.pop('size', -1)) or -1

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'seeders': seeders,
                    'leechers': leechers,
                    'pubdate': None,
                }
                if mode != 'RSS':
                    sickrage.srCore.srLogger.debug('Found result: {}'.format(title))

                items.append(item)
            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                sickrage.srCore.srLogger.error('Failed parsing provider')

        return items

    @staticmethod
    def _check_auth_from_data(data):
        if not all([isinstance(data, dict),
                    data.pop('status', 200) != 401,
                    data.pop('message', '') != 'Invalid API key']):

            sickrage.srCore.srLogger.warning('Invalid api key. Check your settings')
            return False

        return True
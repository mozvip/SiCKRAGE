# Author: Idan Gutman
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

import sickrage
from sickrage.core.caches.tv_cache import TVCache
from sickrage.core.helpers import bs4_parser
from sickrage.providers import TorrentProvider


class SceneTimeProvider(TorrentProvider):
    def __init__(self):
        super(SceneTimeProvider, self).__init__("SceneTime", 'http://www.scenetime.com', True)

        self.urls.update({
            'login': '{base_url}/takelogin.php'.format(**self.urls),
            'detail': '{base_url}/details.php?id=%s'.format(**self.urls),
            'search': '{base_url}/browse_API.php'.format(**self.urls),
            'download': '{base_url}/download.php/%s/%s'.format(**self.urls)
        })

        self.username = None
        self.password = None

        self.minseed = None
        self.minleech = None

        self.enable_cookies = True
        self.required_cookies = ('uid', 'pass')

        self.categories = [2, 42, 9, 63, 77, 79, 100, 83]

        self.cache = TVCache(self, min_time=20)

    def login(self):
        return self.cookie_login('sign in')

    def search(self, search_params, age=0, ep_obj=None):
        results = []

        if not self.login():
            return results

        for mode in search_params.keys():
            sickrage.srCore.srLogger.debug("Search Mode: %s" % mode)
            for search_string in search_params[mode]:
                if mode != 'RSS':
                    sickrage.srCore.srLogger.debug("Search string: %s " % search_string)

                query = {'sec': 'jax', 'cata': 'yes', 'search': search_string}
                query.update({"c%s" % i: 1 for i in self.categories})

                try:
                    data = sickrage.srCore.srWebSession.post(self.urls['search'], data=query).text
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

        with bs4_parser(data) as html:
            torrent_rows = html.findAll('tr')

            # Continue only if one Release is found
            if len(torrent_rows) < 2:
                sickrage.srCore.srLogger.debug("Data returned from provider does not contain any torrents")
                return results

            # Scenetime apparently uses different number of cells in #torrenttable based
            # on who you are. This works around that by extracting labels from the first
            # <tr> and using their index to find the correct download/seeders/leechers td.
            labels = [label.get_text() for label in torrent_rows[0].find_all('td')]

            for result in torrent_rows[1:]:
                cells = result.find_all('td')

                link = cells[labels.index('Name')].find('a')

                full_id = link['href'].replace('details.php?id=', '')
                torrent_id = full_id.split("&")[0]

                try:
                    title = link.contents[0].get_text()
                    filename = "%s.torrent" % title.replace(" ", ".")
                    download_url = self.urls['download'] % (torrent_id, filename)

                    int(cells[labels.index('Seeders')].get_text())
                    seeders = int(cells[labels.index('Seeders')].get_text())
                    leechers = int(cells[labels.index('Leechers')].get_text())
                    # FIXME
                    size = -1

                    if not all([title, download_url]):
                        continue

                    item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders,
                            'leechers': leechers, 'hash': ''}

                    if mode != 'RSS':
                        sickrage.srCore.srLogger.debug("Found result: {}".format(title))

                    results.append(item)
                except Exception:
                    sickrage.srCore.srLogger.error("Failed parsing provider")

        return results
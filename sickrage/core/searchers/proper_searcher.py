# Author: echel0n <echel0n@sickrage.ca>
# URL: https://sickrage.ca
# Git: https://git.sickrage.ca/SiCKRAGE/sickrage.git
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

import datetime
import operator
import re
import threading
import time
import traceback

import sickrage
from sickrage.core.common import DOWNLOADED, Quality, SNATCHED, SNATCHED_PROPER, cpu_presets
from sickrage.core.exceptions import AuthException
from sickrage.core.helpers import remove_non_release_groups
from sickrage.core.nameparser import InvalidNameException, InvalidShowException, NameParser
from sickrage.core.search import pickBestResult, snatchEpisode
from sickrage.core.tv.show.history import History
from sickrage.providers import NZBProvider, NewznabProvider, TorrentProvider, TorrentRssProvider


class srProperSearcher(object):
    def __init__(self, *args, **kwargs):
        self.name = "PROPERSEARCHER"
        self.amActive = False

    def run(self, force=False):
        """
        Start looking for new propers
        :param force: Start even if already running (currently not used, defaults to False)
        """
        if self.amActive or sickrage.srCore.srConfig.DEVELOPER and not force:
            return

        self.amActive = True

        # set thread name
        threading.currentThread().setName(self.name)

        sickrage.srCore.srLogger.info("Beginning the search for new propers")
        propers = self._getProperList()

        if propers:
            self._downloadPropers(propers)

        self._set_lastProperSearch(datetime.datetime.today().toordinal())

        sickrage.srCore.srLogger.info("Completed the search for new propers")

        self.amActive = False

    def _getProperList(self):
        """
        Walk providers for propers
        """
        propers = {}

        search_date = datetime.datetime.today() - datetime.timedelta(days=2)

        origThreadName = threading.currentThread().getName()

        recently_aired = []
        for show in [s['doc'] for s in sickrage.srCore.mainDB.db.all('tv_shows', with_doc=True)]:
            for episode in [e['doc'] for e in
                            sickrage.srCore.mainDB.db.get_many('tv_episodes', show['indexer_id'], with_doc=True)]:
                if episode['airdate'] >= str(search_date.toordinal()):
                    if episode['status'] in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_BEST:
                        recently_aired += [episode]

        if not recently_aired:
            sickrage.srCore.srLogger.info('No recently aired episodes, nothing to search for')
            return []

        # for each provider get a list of the
        for providerID, providerObj in sickrage.srCore.providersDict.sort(
                randomize=sickrage.srCore.srConfig.RANDOMIZE_PROVIDERS).items():
            # check provider type and provider is enabled
            if not sickrage.srCore.srConfig.USE_NZBS and providerObj.type in [NZBProvider.type,
                                                                              NewznabProvider.type]:
                continue
            elif not sickrage.srCore.srConfig.USE_TORRENTS and providerObj.type in [TorrentProvider.type,
                                                                                    TorrentRssProvider.type]:
                continue
            elif not providerObj.isEnabled:
                continue

            threading.currentThread().setName(origThreadName + " :: [" + providerObj.name + "]")

            sickrage.srCore.srLogger.info("Searching for any new PROPER releases from " + providerObj.name)

            try:
                curPropers = providerObj.find_propers(recently_aired)
            except AuthException as e:
                sickrage.srCore.srLogger.warning("Authentication error: {}".format(e.message))
                continue
            except Exception as e:
                sickrage.srCore.srLogger.debug(
                    "Error while searching " + providerObj.name + ", skipping: {}".format(e.message))
                sickrage.srCore.srLogger.debug(traceback.format_exc())
                continue

            # if they haven't been added by a different provider than add the proper to the list
            for x in curPropers:
                if not re.search(r'(^|[\. _-])(proper|repack)([\. _-]|$)', x.name, re.I):
                    sickrage.srCore.srLogger.debug('findPropers returned a non-proper, we have caught and skipped it.')
                    continue

                name = self._genericName(x.name)
                if not name in propers:
                    sickrage.srCore.srLogger.debug("Found new proper: " + x.name)
                    x.provider = providerObj
                    propers[name] = x

            threading.currentThread().setName(origThreadName)

        # take the list of unique propers and get it sorted by
        sortedPropers = sorted(propers.values(), key=operator.attrgetter('date'), reverse=True)
        finalPropers = []

        for curProper in sortedPropers:

            try:
                myParser = NameParser(False)
                parse_result = myParser.parse(curProper.name)
            except InvalidNameException:
                sickrage.srCore.srLogger.debug(
                    "Unable to parse the filename " + curProper.name + " into a valid episode")
                continue
            except InvalidShowException:
                sickrage.srCore.srLogger.debug("Unable to parse the filename " + curProper.name + " into a valid show")
                continue

            if not parse_result.series_name:
                continue

            if not parse_result.episode_numbers:
                sickrage.srCore.srLogger.debug(
                    "Ignoring " + curProper.name + " because it's for a full season rather than specific episode")
                continue

            sickrage.srCore.srLogger.debug(
                "Successful match! Result " + parse_result.original_name + " matched to show " + parse_result.show.name)

            # set the indexerid in the db to the show's indexerid
            curProper.indexerid = parse_result.indexerid

            # set the indexer in the db to the show's indexer
            curProper.indexer = parse_result.show.indexer

            # populate our Proper instance
            curProper.show = parse_result.show
            curProper.season = parse_result.season_number if parse_result.season_number is not None else 1
            curProper.episode = parse_result.episode_numbers[0]
            curProper.release_group = parse_result.release_group
            curProper.version = parse_result.version
            curProper.quality = Quality.nameQuality(curProper.name, parse_result.is_anime)
            curProper.content = None

            # filter release
            bestResult = pickBestResult(curProper, parse_result.show)
            if not bestResult:
                sickrage.srCore.srLogger.debug("Proper " + curProper.name + " were rejected by our release filters.")
                continue

            # only get anime proper if it has release group and version
            if bestResult.show.is_anime:
                if not bestResult.release_group and bestResult.version == -1:
                    sickrage.srCore.srLogger.debug(
                        "Proper " + bestResult.name + " doesn't have a release group and version, ignoring it")
                    continue

            # check if we actually want this proper (if it's the right quality)            
            dbData = [x['doc'] for x in
                      sickrage.srCore.mainDB().db.get_many('tv_episodes', bestResult.indexerid, with_doc=True)
                      if x['doc']['season'] == bestResult.season and x['doc']['episode'] == bestResult.episode]
            if not dbData: continue

            # only keep the proper if we have already retrieved the same quality ep (don't get better/worse ones)
            oldStatus, oldQuality = Quality.splitCompositeStatus(int(dbData[0]["status"]))
            if oldStatus not in (DOWNLOADED, SNATCHED) or oldQuality != bestResult.quality:
                continue

            # check if we actually want this proper (if it's the right release group and a higher version)
            if bestResult.show.is_anime:
                dbData = [x['doc'] for x in
                          sickrage.srCore.mainDB.db.get_many('tv_episodes', bestResult.indexerid, with_doc=True)
                          if x['doc']['season'] == bestResult.season and x['doc']['episode'] == bestResult.episode]

                oldVersion = int(dbData[0]["version"])
                oldRelease_group = (dbData[0]["release_group"])

                if -1 < oldVersion < bestResult.version:
                    sickrage.srCore.srLogger.info(
                        "Found new anime v" + str(bestResult.version) + " to replace existing v" + str(oldVersion))
                else:
                    continue

                if oldRelease_group != bestResult.release_group:
                    sickrage.srCore.srLogger.info(
                        "Skipping proper from release group: " + bestResult.release_group + ", does not match existing release group: " + oldRelease_group)
                    continue

            # if the show is in our list and there hasn't been a proper already added for that particular episode then add it to our list of propers
            if bestResult.indexerid != -1 and (bestResult.indexerid, bestResult.season, bestResult.episode) not in map(
                    operator.attrgetter('indexerid', 'season', 'episode'), finalPropers):
                sickrage.srCore.srLogger.info("Found a proper that we need: " + str(bestResult.name))
                finalPropers.append(bestResult)

        return finalPropers

    def _downloadPropers(self, properList):
        """
        Download proper (snatch it)

        :param properList:
        """

        for curProper in properList:
            historyLimit = datetime.datetime.today() - datetime.timedelta(days=30)

            # make sure the episode has been downloaded before
            historyResults = [x for x in
                              sickrage.srCore.mainDB.db.get_many('history', curProper.indexerid, with_doc=True)
                              if x['doc']['season'] == curProper.season and x['doc']['episode'] == curProper.episode
                              and x['doc']['quality'] == curProper.quality
                              and x['doc']['date'] >= historyLimit.strftime(History.date_format)
                              and x['doc']['action'] in Quality.SNATCHED + Quality.DOWNLOADED]

            # if we didn't download this episode in the first place we don't know what quality to use for the proper so we can't do it
            if len(historyResults) == 0:
                sickrage.srCore.srLogger.info(
                    "Unable to find an original history entry for proper " + curProper.name + " so I'm not downloading it.")
                continue

            else:

                # make sure that none of the existing history downloads are the same proper we're trying to download
                clean_proper_name = self._genericName(remove_non_release_groups(curProper.name))
                isSame = False
                for curResult in historyResults:
                    # if the result exists in history already we need to skip it
                    if self._genericName(
                            remove_non_release_groups(curResult["resource"])) == clean_proper_name:
                        isSame = True
                        break
                if isSame:
                    sickrage.srCore.srLogger.debug("This proper is already in history, skipping it")
                    continue

                # make the result object
                result = curProper.provider.getResult([curProper.show.getEpisode(curProper.season, curProper.episode)])
                result.show = curProper.show
                result.url = curProper.url
                result.name = curProper.name
                result.quality = curProper.quality
                result.release_group = curProper.release_group
                result.version = curProper.version
                result.seeders = curProper.seeders
                result.leechers = curProper.leechers
                result.size = curProper.size
                result.files = curProper.files
                result.content = curProper.content

                # snatch it
                snatchEpisode(result, SNATCHED_PROPER)
                time.sleep(cpu_presets[sickrage.srCore.srConfig.CPU_PRESET])

    def _genericName(self, name):
        return name.replace(".", " ").replace("-", " ").replace("_", " ").lower()

    def _set_lastProperSearch(self, when):
        """
        Record last propersearch in DB

        :param when: When was the last proper search
        """

        sickrage.srCore.srLogger.debug("Setting the last proper search in database to " + str(when))

        dbData = [x['doc'] for x in sickrage.srCore.mainDB.db.all('info', with_doc=True)]
        if len(dbData) == 0:
            sickrage.srCore.mainDB.db.insert({
                '_t': 'info',
                'last_backlog': 0,
                'last_indexer': 0,
                'last_proper_search': str(when)
            })
        else:
            dbData[0]['last_proper_search'] = str(when)
            sickrage.srCore.mainDB.db.update(dbData[0])

    @staticmethod
    def _get_lastProperSearch():
        """
        Find last propersearch from DB
        """

        try:
            dbData = [x['doc'] for x in sickrage.srCore.mainDB.db.all('info', with_doc=True)]
            last_proper_search = datetime.date.fromordinal(int(dbData[0]["last_proper_search"]))
        except:
            last_proper_search = datetime.date.fromordinal(1)

        return last_proper_search

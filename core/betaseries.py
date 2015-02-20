import xbmc
import sys, traceback
import time
import settings
import urllib, urllib2, socket, hashlib, time, platform
import simplejson as json
import hashlib
from utils import get_urldata, extract_shows_info_from_directory_filename


class BetaSeriesObject:
    def __init__(self):
        self.service = 'betaseries'
        self.token = ''
        self.authfail = False
        self.failurecount = 0
        self.timercounter = 0
        self.timerexpiretime = 0

    def getService(self):
        return self.service

    def setToken(self, token):
        self.token = token

    def getToken(self):
        return self.token

    def setAuthFail(self, authfail):
        self.authfail = authfail

    def getAuthFail(self):
        return self.authfail

    def setFailureCount(self, failurecount):
        self.failurecount = failurecount

    def getFailureCount(self):
        return self.failurecount

    def setTimerCounter(self, timercounter):
        self.timercounter = timercounter

    def getTimerCounter(self):
        return self.timercounter

    def setTimerExpireTime(self, timerexpiretime):
        self.timerexpiretime = timerexpiretime

    def getTimerExpireTime(self):
        return self.timerexpiretime

    def incrementFailureCount(self):
        self.failurecount += 1

    def incrementTimerCounter(self):
        self.timercounter *= 2


class EpisodeObject():
    def __init__(self):
        self.tvdbid = -1
        self.tvdbepid = -1
        self.showtitle = ''
        self.epname = ''
        self.season = '-1'
        self.episode = '-1'
        self.showalreadyadded = False
        self.episodealreadydownloaded = False

    def __init__(self, tvdbid, tvdbepid, showtitle, epname, season, episode, showalreadyadded,
                 episodealreadydownloaded):
        self.tvdbid = tvdbid
        self.tvdbepid = tvdbepid
        self.showtitle = showtitle
        self.epname = epname
        self.season = season
        self.episode = episode
        self.showalreadyadded = showalreadyadded
        self.episodealreadydownloaded = episodealreadydownloaded

    def getTvdbId(self):
        return self.tvdbid

    def setTvdbId(self, id):
        self.tvdbid = id

    def getTvdbEpId(self):
        return self.tvdbepid

    def setTvbEpId(self, id):
        self.tvdbepid = id

    def getShowTitle(self):
        return self.showtitle

    def setShowTitle(self, title):
        self.showtitle = title

    def getEpName(self):
        return self.epname

    def setEpName(self, epname):
        self.epname = epname

    def getSeason(self):
        return self.season

    def setSeason(self, season):
        self.season = season

    def getEpisode(self):
        return self.episode

    def setEpisode(self, episode):
        self.episode = episode

    def getShowAlreadAdded(self):
        return self.showalreadyadded

    def setShowALreadAdded(self, showalreadyadded):
        self.showalreadyadded = showalreadyadded

    def getEpisodeAlreadyDownloaded(self):
        return self.episodealreadydownloaded

    def setEpisodeAlreadyDownloaded(self, episodealreadydownloaded):
        self.episodealreadydownloaded = episodealreadydownloaded


class BetaSeriesDownloaded:
    def __init__(self, user_agent):
        self.betaserie_object = BetaSeriesObject()
        self.user_agent = user_agent

    def _get_info(self, show_file):
        xbmc.log(settings.LOG_ADDON_NAME + "*** IN BetaSeriesDownloaded._get_info : %s" % show_file, xbmc.LOGDEBUG)

        epinfo = {}

        if len(show_file) > 0:
            infos_show_title = show_file[0]
            infos_show_season = show_file[1]
            infos_show_episode = show_file[2]

            tvdbid = -1

            xbmc.log(settings.LOG_ADDON_NAME + "SHOW: %s EPISODE : %s.%s" % (
                infos_show_title, infos_show_season, infos_show_episode), xbmc.LOGDEBUG)

            url = settings.API_URL + '/shows/search'
            urldata = [['v', settings.API_VER], ['key', settings.API_KEY], ['title', infos_show_title]]
            try:
                xbmc.log(settings.LOG_ADDON_NAME + "Try to get infos from betaseries", xbmc.LOGDEBUG)

                tvdbid_query = get_urldata(self.user_agent, url, urldata, "GET")
                tvdbid_query = json.loads(tvdbid_query)

                for show in tvdbid_query['shows']:
                    if show['title'].lower() == infos_show_title:
                        tvdbid = show['thetvdb_id']
                        showtitle = show['title']

                if tvdbid == -1:
                    xbmc.log(settings.LOG_ADDON_NAME + "Show %s not found" % infos_show_title, xbmc.LOGNOTICE)
                    return False

                xbmc.log(settings.LOG_ADDON_NAME + "Infos got from betaseries : %s " % tvdbid, xbmc.LOGDEBUG)
            except:
                xbmc.log(
                    settings.LOG_ADDON_NAME + "could not fetch tvshow's thetvdb_id, tshow itle: %s" % infos_show_title,
                    xbmc.LOGNOTICE)
                return False

            xbmc.log(settings.LOG_ADDON_NAME + "try to get episode", xbmc.LOGDEBUG)
            url = settings.API_URL + '/shows/episodes'
            urldata = [['v', settings.API_VER], ['key', settings.API_KEY], ['thetvdb_id', str(tvdbid)],
                       ['season', infos_show_season], ['episode', infos_show_episode],
                       ['token', self.betaserie_object.getToken()]]
            try:
                tvdbepid_query = get_urldata(self.user_agent, url, urldata, "GET")
                tvdbepid_query = json.loads(tvdbepid_query)
                tvdbepid = tvdbepid_query['episodes'][0]['thetvdb_id']
                downloaded = tvdbepid_query['episodes'][0]['user']['downloaded']
                epname = tvdbepid_query['episodes'][0]['title']
            except:
                xbmc.log(settings.LOG_ADDON_NAME + "could not fetch episode's thetvdb_id, show title: %s | %s %s " % (
                infos_show_title, url, urldata),
                         xbmc.LOGNOTICE)
                return False

            # to change with the database value ????!!!!
            already_added = False
            epinfo = EpisodeObject(int(tvdbid), int(tvdbepid), showtitle, epname, infos_show_season, infos_show_episode,
                                   already_added, downloaded)

            xbmc.log(settings.LOG_ADDON_NAME + "*** OUT BetaSeriesObject._get_info *****", xbmc.LOGDEBUG)
        return epinfo

    def _service_betaserie(self, file):
        xbmc.log(settings.LOG_ADDON_NAME + "*** IN BetaSeriesObject._service_betaserie", xbmc.LOGDEBUG)

        tstamp = int(time.time())
        # don't proceed if we had an authentication failure
        if not self.betaserie_object.getAuthFail():
            # test if we are authenticated
            if not self.betaserie_object.getToken():
                # authenticate
                self._service_authenticate(str(tstamp))

            # only proceed if authentication was succesful
            if self.betaserie_object.getToken():
                episode = self._get_info(file)
                # mark if we still have a valid session key after submission and have episode info
                if episode and episode.getTvdbId() != -1 and episode.getTvdbEpId() != -1:
                    self._service_mark_as_downloaded(episode)

        xbmc.log(settings.LOG_ADDON_NAME + "*** OUT BetaSeriesObject._service_betaserie", xbmc.LOGDEBUG)

    def _service_authenticate(self, timestamp):
        xbmc.log(settings.LOG_ADDON_NAME + "*** IN BetaSeriesObject._service_authenticate", xbmc.LOGDEBUG)

        # don't proceed if timeout timer has not expired
        if self.betaserie_object.getTimerExpireTime() > int(timestamp):
            xbmc.log(settings.LOG_ADDON_NAME + "timeout timer has not expired", xbmc.LOGNOTICE)
            return

        # create a pass hash
        md5pass = hashlib.md5()
        md5pass.update(settings.BETA_PASS)
        url = settings.API_URL + '/members/auth'
        urldata = {'v': settings.API_VER, 'key': settings.API_KEY, 'login': settings.BETA_USER,
                   'password': md5pass.hexdigest()}
        try:
            # authentication request
            response = get_urldata(self.user_agent, url, urldata, "POST")
            # authentication response
            data = json.loads(response)
            xbmc.log(settings.LOG_ADDON_NAME + "successfully authenticated", xbmc.LOGNOTICE)
        except:
            self._service_fail(True)
            xbmc.executebuiltin(
                (u'Notification(%s,%s,%s,%s)' % (
                    settings.LOG_ADDON_NAME, settings.ADDON_TRAD(40006), 750, settings.ADDON_ICON)).encode('utf-8',
                                                                                                           'ignore'))
            xbmc.log(settings.LOG_ADDON_NAME + "failed to connect for authentication", xbmc.LOGNOTICE)
            return

        # parse results
        if 'token' in data:
            # get token
            self.betaserie_object.setToken(str(data['token']))
            # reset failure count
            self.betaserie_object.setFailureCount(0)
            # reset timer
            self.betaserie_object.setTimerCounter(0)
            self.betaserie_object.setTimerExpireTime(0)
        if data['errors']:
            xbmc.log(settings.LOG_ADDON_NAME + "%s error %s : %s" % (
                self.betaserie_object.getService(), data['errors'][0]['code'], data['errors'][0]['text']),
                     xbmc.LOGNOTICE)
            if data['errors'][0]['code'] < 2000:
                # API error
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (
                        settings.ADDON_NAME, settings.ADDON_TRAD(40005), 750, settings.ADDON_ICON)).encode(
                        'utf-8',
                        'ignore'))
                xbmc.log(settings.LOG_ADDON_NAME + "bad API usage", xbmc.LOGNOTICE)
                # disable the service, the monitor class will pick up the changes
                settings.ADDON.setSetting('betaactive', 'false')
            elif data['errors'][0]['code'] > 4001:
                # login error
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (
                        settings.ADDON_NAME, settings.ADDON_TRAD(40007), 750, settings.ADDON_ICON)).encode('utf-8',
                                                                                                           'ignore'))
                xbmc.log(settings.LOG_ADDON_NAME + "login or password incorrect", xbmc.LOGNOTICE)
                self.betaserie_object.setAuthFail(True)
            else:
                # everything else
                self._service_fail(True)
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (
                        settings.ADDON_NAME, settings.ADDON_TRAD(40004), 750, settings.ADDON_ICON)).encode('utf-8',
                                                                                                           'ignore'))
                xbmc.log(settings.LOG_ADDON_NAME + "server error while authenticating", xbmc.LOGNOTICE)

        xbmc.log(settings.LOG_ADDON_NAME + "*** OUT BetaSeries._service_authenticate", xbmc.LOGDEBUG)

    def _get_episode_already_in_account(self):
        xbmc.log(settings.LOG_ADDON_NAME + "*** IN BetaSeries._get_episode_already_in_account", xbmc.LOGDEBUG)
        episodes_to_download = {}

        tstamp = int(time.time())
        # don't proceed if we had an authentication failure
        if not self.betaserie_object.getAuthFail():
            # test if we are authenticated
            if not self.betaserie_object.getToken():
                # authenticate
                self._service_authenticate(str(tstamp))

            # only proceed if authentication was succesful
            if self.betaserie_object.getToken():
                url = settings.API_URL + '/episodes/list'
                urldata = [['v', settings.API_VER], ['key', settings.API_KEY],
                           ['token', self.betaserie_object.getToken()]]
                # try:
                xbmc.log(settings.LOG_ADDON_NAME + "Try to get episodes to see from betaseries", xbmc.LOGDEBUG)

                account_infos = get_urldata(self.user_agent, url, urldata, "GET")
                account_infos = json.loads(account_infos)

                for show in account_infos['shows']:
                    # xbmc.log(settings.LOG_ADDON_NAME + "Show : %s" % show['title'], xbmc.LOGDEBUG)
                    list_season_episode = {}
                    for episode in show['unseen']:
                        # xbmc.log(settings.LOG_ADDON_NAME + "Episode : %s" % episode['title'].encode('utf-8'), xbmc.LOGDEBUG)
                        downloaded = episode['user']['downloaded']
                        if downloaded:
                            # show 1
                            # |- season 1
                            # |- episode 1
                            #       |- episode 2
                            #   |- season 2
                            #       |- episode 1
                            # show 2
                            #   |- season 1
                            #       |- episode 1
                            show_season = episode['season']
                            show_episode = episode['episode']

                            xbmc.log(settings.LOG_ADDON_NAME + "Show %s, Episode %s.%s" % (
                            show['title'], show_season, show_episode), xbmc.LOGDEBUG)

                            if show_season in list_season_episode:
                                list_season_episode[show_season].append(show_episode)
                            else:
                                list_season_episode[show_season] = [show_episode]

                    if len(list_season_episode) > 0:
                        show_title = show['title'].lower()
                        episodes_to_download[show_title] = list_season_episode
                        xbmc.log(settings.LOG_ADDON_NAME + "%s => %s" % (show_title, list_season_episode),
                                 xbmc.LOGDEBUG)

                xbmc.log(settings.LOG_ADDON_NAME + "Episodes to see got from betaseries", xbmc.LOGDEBUG)
                # except:
                # xbmc.log(settings.LOG_ADDON_NAME + "could not fetch episodes to see %s" % ''.join(traceback.format_exception(*sys.exc_info())).encode('utf-8'), xbmc.LOGNOTICE)
                # return False

        xbmc.log(settings.LOG_ADDON_NAME + "*** OUT BetaSeries._get_episode_already_in_account", xbmc.LOGDEBUG)

        return episodes_to_download

    def _service_mark_as_downloaded(self, episode):
        xbmc.log(settings.LOG_ADDON_NAME + "*** IN BetaSeries._service_mark_as_downloaded *******", xbmc.LOGDEBUG)
        xbmc.log(settings.LOG_ADDON_NAME + "Episode %s.%s: " % (episode.getSeason(), episode.getEpisode()),
                 xbmc.LOGDEBUG)

        # episode not already marked as downloaded
        if not episode.getEpisodeAlreadyDownloaded():
            xbmc.log(settings.LOG_ADDON_NAME + "Mark show as followed: %s, Show already added: %s" %
                     (str(settings.BETA_FOLLOW), str(episode.getShowAlreadAdded())), xbmc.LOGNOTICE)
            # want to add the show to the account and the show is not already added
            if settings.BETA_FOLLOW and not episode.getShowAlreadAdded():
                url = settings.API_URL + "/shows/show"
                urldata = {'v': settings.API_VER, 'key': settings.API_KEY, 'token': self.betaserie_object.getToken(),
                           'thetvdb_id': episode.getTvdbId()}
                try:
                    # marking request
                    response = get_urldata(self.user_agent, url, urldata, "POST")
                    # marking response
                    data = json.loads(response)
                except:
                    self._service_fail(False)
                    xbmc.log(settings.LOG_ADDON_NAME + "failed to follow show %s" % episode.getShowTitle(),
                             xbmc.LOGNOTICE)
                    return
                # parse results
                if data['errors']:
                    if data['errors'][0]['code'] == 2001:
                        # drop our session key
                        self.betaserie_object.setToken('')
                        xbmc.log(settings.LOG_ADDON_NAME + "bad token while following show", xbmc.LOGNOTICE)
                        return
                    elif data['errors'][0]['code'] == 2003:
                        xbmc.log(settings.LOG_ADDON_NAME + "already following show %s" % episode.getShowTitle(),
                                 xbmc.LOGNOTICE)
                    else:
                        xbmc.executebuiltin((u'Notification(%s,%s,%s,%s)' % (
                            settings.ADDON_NAME, settings.ADDON_TRAD(40008) + episode.getShowTitle().decode('utf-8'),
                            750, settings.ADDON_ICON)).encode(
                            'utf-8',
                            'ignore'))
                        xbmc.log(settings.LOG_ADDON_NAME + "failed to follow show %s" % episode.getShowTitle(),
                                 xbmc.LOGNOTICE)
                        return
                else:
                    if settings.BETA_NOTIFY:
                        xbmc.executebuiltin((u'Notification(%s,%s,%s,%s,%s,%s,%s)' % (
                            settings.ADDON_NAME, settings.ADDON_TRAD(40002), episode.getShowTitle(),
                            episode.getSeason(), episode.getEpisode(), 750, settings.ADDON_ICON)).encode(
                            'utf-8',
                            'ignore'))
                    xbmc.log(settings.LOG_ADDON_NAME + "now following show %s" % (episode.getShowTitle()),
                             xbmc.LOGNOTICE)
            # mark episode as downloaded
            url = settings.API_URL + "/episodes/downloaded"
            urldata = {'v': settings.API_VER, 'key': settings.API_KEY, 'token': self.betaserie_object.getToken(),
                       'thetvdb_id': episode.getTvdbEpId()}
            try:
                # marking request
                response = get_urldata(self.user_agent, url, urldata, "POST")
                # marking response
                data = json.loads(response)
            except:
                self._service_fail(False)
                xbmc.log(settings.LOG_ADDON_NAME + "failed to mark as downloaded", xbmc.LOGNOTICE)
                return

            # parse results
            if data['errors']:
                if data['errors'][0]['code'] == 2001:
                    # drop our session key
                    self.betaserie_object.setToken('')
                    xbmc.log(settings.LOG_ADDON_NAME + "bad token while marking episode", xbmc.LOGNOTICE)
                elif data['errors'][0]['code'] == 0:
                    xbmc.log(
                        settings.LOG_ADDON_NAME + "not following show, or episode %s already marked as downloaded" %
                        episode.getEpName(),
                        xbmc.LOGNOTICE)
                else:
                    xbmc.executebuiltin(
                        (u'Notification(%s,%s,%s,%s)' % (
                            settings.ADDON_NAME, settings.ADDON_TRAD(40009), 750, settings.ADDON_ICON)).encode(
                            'utf-8',
                            'ignore'))
                    xbmc.log(settings.LOG_ADDON_NAME + "error marking episode %s as downloaded" % episode.getEpName(),
                             xbmc.LOGNOTICE)
            else:
                if settings.BETA_NOTIFY:
                    xbmc.executebuiltin(
                        (u'Notification(%s,%s,%s,%s)' % (
                            settings.ADDON_NAME, settings.ADDON_TRAD(40003), 750, settings.ADDON_ICON)).encode(
                            'utf-8', 'ignore'))
                xbmc.log(settings.LOG_ADDON_NAME + "%s episode %s.%s marked as downloaded" % (
                    episode.getShowTitle(), episode.getSeason(), episode.getEpisode()), xbmc.LOGNOTICE)

        xbmc.log(settings.LOG_ADDON_NAME + "*** OUT BetaSeries._service_mark_as_downloaded *******", xbmc.LOGDEBUG)

    def _service_fail(self, timer):
        timestamp = int(time.time())

        # increment failure counter
        self.betaserie_object.incrementFailureCount()

        # drop our session key if we encouter three failures
        if self.betaserie_object.getFailureCount() > 2:
            self.betaserie_object.setToken('')

        # set a timer if failure occurred during authentication phase
        if timer:
            # wrap timer if we cycled through all timeout values
            if self.betaserie_object.getTimerCounter() == 0 or self.betaserie_object.getTimerCounter() == 7680:
                self.betaserie_object.setTimerCounter(60)
            else:
                # increment timer
                self.betaserie_object.incrementTimerCounter()

        # set timer expire time
        self.betaserie_object.setTimerExpireTime(timestamp + self.betaserie_object.getTimerCounter())
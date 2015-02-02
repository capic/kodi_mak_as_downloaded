import xbmc
import time
import settings
import urllib, urllib2, socket, hashlib, time, platform
import simplejson as json
import hashlib
from utils import get_urldata, extract_shows_info_from_filename

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

    def __init__(self, tvdbid, tvdbepid, showtitle, epname, season, episode, showalreadyadded, episodealreadydownloaded):
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
        self.betaserieobject = BetaSeriesObject()
        self.user_agent = user_agent

    def _get_info(self, showfile):
        xbmc.log(settings.LOG_ADDON_NAME + "_get_info : %s" % showfile, xbmc.LOGDEBUG)

        epinfo = {}
        infosshow = extract_shows_info_from_filename(showfile)

        if len(infosshow) > 0:
            infosshowtitle = infosshow[0]
            infosshowseason = infosshow[1]
            infosshowepisode = infosshow[2]

            xbmc.log(settings.LOG_ADDON_NAME + "_______________ SERIE : %s EPISODE : %s.%s" % (infosshowtitle, infosshowseason, infosshowepisode))

            url = settings.API_URL + '/shows/search'
            urldata = [['v', settings.API_VER], ['key', settings.API_KEY], ['title', infosshowtitle]]
            try:
                xbmc.log(settings.LOG_ADDON_NAME + "Try to get infos from betaseries")

                tvdbid_query = get_urldata(self.user_agent, url, urldata, "GET")
                tvdbid_query = json.loads(tvdbid_query)
                tvdbid = tvdbid_query['shows'][0]['thetvdb_id']
                showtitle = tvdbid_query['shows'][0]['title']

                xbmc.log(settings.LOG_ADDON_NAME + "Infos got from betaseries : %s " % tvdbid)
            except:
                xbmc.log(settings.LOG_ADDON_NAME + "could not fetch tvshow's thetvdb_id", xbmc.LOGDEBUG)
                return False

            xbmc.log(settings.LOG_ADDON_NAME + "try to get episode")
            url = settings.API_URL + '/shows/episodes'
            #pass the user !!!!!!!
            urldata = [['v', settings.API_VER], ['key', settings.API_KEY], ['thetvdb_id', str(tvdbid)], ['season', infosshowseason], ['episode', infosshowepisode], ['token', self.betaserieobject.getToken()]]
            try:
                tvdbepid_query = get_urldata(self.user_agent, url, urldata, "GET")
                tvdbepid_query = json.loads(tvdbepid_query)
                tvdbepid = tvdbepid_query['episodes'][0]['thetvdb_id']
                downloaded = tvdbepid_query['episodes'][0]['user']['downloaded']
                epname = tvdbepid_query['episodes'][0]['title']
            except:
                xbmc.log(settings.LOG_ADDON_NAME + "could not fetch episode's thetvdb_id %s %s " % (url, urldata),
                         xbmc.LOGNOTICE)
                return False

            alreadyadded = False
            epinfo = EpisodeObject(int(tvdbid), int(tvdbepid), showtitle, epname, infosshowseason, infosshowepisode, alreadyadded, downloaded)

            xbmc.log(settings.LOG_ADDON_NAME + "OUT ***** MyVideoLibrary._get_info *****")
        return epinfo

    # episode: [[int(tvdbid), int(tvdbepid), showtitle, epname, alreadyadded, downloaded]
    # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
    def _service_betaserie(self, file):
        xbmc.log(settings.LOG_ADDON_NAME + "Main._service_betaserie")

        tstamp = int(time.time())
        # don't proceed if we had an authentication failure
        if not self.betaserieobject.getAuthFail():
            # test if we are authenticated
            if not self.betaserieobject.getToken():
                # authenticate
                self._service_authenticate(str(tstamp))

            # only proceed if authentication was succesful
            if self.betaserieobject.getToken():
                episode = self._get_info(file)
                # mark if we still have a valid session key after submission and have episode info
                if episode and episode.getTvdbId() != -1 and episode.getTvdbEpId() != -1:
                    self._service_mark_as_downloaded(episode)

    # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
    def _service_authenticate(self, timestamp):
        xbmc.log(settings.LOG_ADDON_NAME + "Main._service_authenticate")

        # don't proceed if timeout timer has not expired
        if self.betaserieobject.getTimerExpireTime() > int(timestamp):
            xbmc.log(settings.LOG_ADDON_NAME + "timeout timer has not expired")
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
            xbmc.log(settings.LOG_ADDON_NAME + "successfully authenticated")
        except:
            self._service_fail(True)
            xbmc.executebuiltin(
                (u'Notification(%s,%s,%s,%s)' % (settings.LOG_ADDON_NAME, 32003, 750, "")).encode('utf-8',
                                                                                                  'ignore'))
            xbmc.log(settings.LOG_ADDON_NAME + "failed to connect for authentication")
            return

        # parse results
        if 'token' in data:
            # get token
            self.betaserieobject.setToken(str(data['token']))
            # reset failure count
            self.betaserieobject.setFailureCount(0)
            # reset timer
            self.betaserieobject.setTimerCounter(0)
            self.betaserieobject.setTimerExpireTime(0)
        if data['errors']:
            xbmc.log(settings.LOG_ADDON_NAME + "%s error %s : %s" % (
                self.betaserieobject.getService(), data['errors'][0]['code'], data['errors'][0]['text']))
            if data['errors'][0]['code'] < 2000:
                # API error
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (settings.ADDON_NAME, __language__(32002), 750, __icon__)).encode(
                        'utf-8',
                        'ignore'))
                xbmc.log(settings.LOG_ADDON_NAME + "bad API usage")
                # disable the service, the monitor class will pick up the changes
                __addon__.setSetting('betaactive', 'false')
            elif data['errors'][0]['code'] > 4001:
                # login error
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(32004), 750, __icon__)).encode('utf-8',
                                                                                                                'ignore'))
                xbmc.log(settings.LOG_ADDON_NAME + "login or password incorrect", xbmc.LOGNOTICE)
                self.betaserieobject.setAuthFail(True)
            else:
                # everything else
                self._service_fail(True)
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(32001), 750, __icon__)).encode('utf-8',
                                                                                                                'ignore'))
                xbmc.log(settings.LOG_ADDON_NAME + "server error while authenticating", xbmc.LOGNOTICE)

    # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
    # episode: [int(tvdbid), int(tvdbepid), showtitle, epname, alreadyadded, downloaded]
    def _service_mark_as_downloaded(self, episode):
        xbmc.log(settings.LOG_ADDON_NAME + "******IN _service_mark_as_downloaded *******", xbmc.LOGNOTICE)
        xbmc.log(settings.LOG_ADDON_NAME + "episode %s.%s: " % (episode.getSeason(), episode.getEpisode()))

        # episode not already marked as downloaded
        if not episode.getEpisodeAlreadyDownloaded():
            xbmc.log(settings.LOG_ADDON_NAME + "Mark show as followed: %s, Show already added: %s" %
                     (str(settings.BETA_FOLLOW), str(episode.getShowAlreadAdded())))
            # want to add the show to the account and the show is not already added
            if settings.BETA_FOLLOW and not episode.getShowAlreadAdded():
                url = settings.API_URL + "/shows/show"
                urldata = {'v': settings.API_VER, 'key': settings.API_KEY, 'token': self.betaserieobject.getToken(),
                           'thetvdb_id': episode.getTvdbId()}
                try:
                    # marking request
                    response = get_urldata(self.user_agent, url, urldata, "POST")
                    # marking response
                    data = json.loads(response)
                except:
                    self._service_fail(False)
                    xbmc.log(settings.LOG_ADDON_NAME + "failed to follow show %s" % episode.getShowTitle(), xbmc.LOGNOTICE)
                    return
                # parse results
                if data['errors']:
                    if data['errors'][0]['code'] == 2001:
                        # drop our session key
                        self.betaserieobject.setToken('')
                        xbmc.log(settings.LOG_ADDON_NAME + "bad token while following show", xbmc.LOGNOTICE)
                        return
                    elif data['errors'][0]['code'] == 2003:
                        xbmc.log(settings.LOG_ADDON_NAME + "already following show %s" % episode.getShowTitle())
                    else:
                        xbmc.executebuiltin((u'Notification(%s,%s,%s,%s)' % (
                            settings.ADDON_NAME, settings.ADDON_TRAD(32005) + episode.getShowTitle().decode('utf-8'), 750, settings.ADDON_ICON)).encode(
                            'utf-8',
                            'ignore'))
                        xbmc.log(settings.LOG_ADDON_NAME + "failed to follow show %s" % episode.getShowTitle())
                        return
                else:
                    if settings.BETA_NOTIFY:
                        xbmc.executebuiltin((u'Notification(%s,%s,%s,%s,%s,%s,%s)' % (
                            settings.ADDON_NAME, settings.ADDON_TRAD(30013), episode.getShowTitle(), episode.getSeason(), episode.getEpisode(), 750, settings.ADDON_ICON)).encode(
                            'utf-8',
                            'ignore'))
                    xbmc.log(settings.LOG_ADDON_NAME + "now following show %s" % (episode.getShowTitle()))
            # mark episode as downloaded
            url = settings.API_URL + "/episodes/downloaded"
            urldata = {'v': settings.API_VER, 'key': settings.API_KEY, 'token': self.betaserieobject.getToken(),
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
                    self.betaserieobject.setToken('')
                    xbmc.log(settings.LOG_ADDON_NAME + "bad token while marking episode", xbmc.LOGNOTICE)
                elif data['errors'][0]['code'] == 0:
                    xbmc.log(
                        settings.LOG_ADDON_NAME + "not following show, or episode %s already marked as downloaded" %
                        episode.getEpName(),
                        xbmc.LOGNOTICE)
                else:
                    xbmc.executebuiltin(
                        (u'Notification(%s,%s,%s,%s)' % (settings.ADDON_NAME, settings.ADDON_TRAD(32006), 750, settings.ADDON_ICON)).encode(
                            'utf-8',
                            'ignore'))
                    xbmc.log(settings.LOG_ADDON_NAME + "error marking episode %s as downloaded" % episode[5],
                             xbmc.LOGNOTICE)
            else:
                if settings.BETA_NOTIFY:
                    xbmc.executebuiltin(
                        (u'Notification(%s,%s,%s,%s)' % (
                            settings.ADDON_NAME, settings.ADDON_TRAD(30014), 750, settings.ADDON_ICON)).encode(
                            'utf-8', 'ignore'))
                xbmc.log(settings.LOG_ADDON_NAME + "%s episode %s.%s marked as downloaded" % (episode.getShowTitle(), episode.getSeason(), episode.getEpisode()))


    # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
    def _service_fail(self, timer):
        timestamp = int(time.time())

        # increment failure counter
        self.betaserieobject.incrementFailureCount()

        # drop our session key if we encouter three failures
        if self.betaserieobject.getFailureCount() > 2:
            self.betaserieobject.setToken('')

        # set a timer if failure occurred during authentication phase
        if timer:
            # wrap timer if we cycled through all timeout values
            if self.betaserieobject.getTimerCounter() == 0 or self.betaserieobject.getTimerCounter() == 7680:
                self.betaserieobject.setTimerCounter(60)
            else:
                # increment timer
                self.betaserieobject.incrementTimerCounter()

        # set timer expire time
        self.betaserieobject.setTimerExpireTime(timestamp + self.betaserieobject.getTimerCounter())
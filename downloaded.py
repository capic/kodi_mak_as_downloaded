import urllib, urllib2, socket, hashlib, time, platform
import xbmcaddon, xbmc
import simplejson as json
import os
import utils


libs = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'lib')
sys.path.append(libs)

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from polling_local import LocalPoller

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__icon__ = __addon__.getAddonInfo('icon')
__addonversion__ = __addon__.getAddonInfo('version')
__platform__ = platform.system() + " " + platform.release()
__language__ = __addon__.getLocalizedString


def set_user_agent():
    log(__addonname__ + "=> set_user_agent")
    json_query = json.loads(xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }'))
    try:
        major = str(json_query['result']['version']['major'])
        minor = str(json_query['result']['version']['minor'])
        name = 'Kodi' if int(major) >= 14 else 'XBMC'
        version = "%s %s.%s" % (name, major, minor)
    except:
        utils.log(__addonname__ + "=> could not get app version")
        version = "XBMC"
    return "Mozilla/5.0 (compatible; " + __platform__ + "; " + version + "; " + __addonid__ + "/" + __addonversion__ + ")"


def get_urldata(url, urldata, method):
    utils.log(__addonname__ + "=> IN ***** get_urldata *****", xbmc.LOGDEBUG)

    utils.log(__addonname__ + "=> url: %s, urldata: %s, method: %s" % (url, urldata, method), xbmc.LOGDEBUG)

    # create a handler
    handler = urllib2.HTTPSHandler()
    # create an openerdirector instance
    opener = urllib2.build_opener(handler)
    # encode urldata
    body = urllib.urlencode(urldata)
    # build a request
    req = urllib2.Request(url, data=body)
    # add any other information you want
    req.add_header('Accept', 'application/json')
    req.add_header('User-Agent', __useragent__)
    # overload the get method function
    req.get_method = lambda: method
    try:
        # response = urllib2.urlopen(req)
        connection = opener.open(req)
    except urllib2.HTTPError as e:
        connection = e
    if connection.code:
        response = connection.read()

        utils.log(__addonname__ + "=> OUT ***** get_urldata *****", xbmc.LOGDEBUG)
        return response
    else:
        log('response empty')

        utils.log(__addonname__ + "=> OUT ***** get_urldata *****", xbmc.LOGDEBUG)
        return 0


class Main:
    def __init__(self):
        utils.log(__addonname__ + "=> Main.__init__")
        self.observer = Observer()
        self._service_setup()
        while not xbmc.abortRequested:
            xbmc.sleep(1000)
        self.observer.stop()
        self.observer.join()

    def _service_setup(self):
        utils.log(__addonname__ + "=> Main._service_setup")
        self.apikey = '5a85a0adc953'
        self.apiurl = 'https://api.betaseries.com'
        self.apiver = '2.4'
        self.Monitor = MyMonitor(action=self._get_settings)
        self._get_settings()

    def _get_settings(self):
        utils.log(__addonname__ + "=> Main._get_settings")
        utils.log(__addonname__ + "=> reading settings")
        service = []
        betaactive = __addon__.getSetting('betaactive') == 'true'
        betauser = __addon__.getSetting('betauser')
        betapass = __addon__.getSetting('betapass')
        betafollow = __addon__.getSetting('betafollow') == 'true'
        betanotify = __addon__.getSetting('betanotify') == 'true'
        path = __addon__.getSetting('videosource1').decode('utf-8')

        if betaactive and betauser and betapass and path:
            utils.log(__addonname__ + "=> betaactive and betauser and betapass")
            # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
            service = ['betaseries', self.apiurl, self.apikey, betauser, betapass, '', False, 0, 0, 0, betafollow,
                       betanotify]
            # self.videoLibrary = MyVideoLibrary(action=self._service_betaserie, service=service)

            event_handler = EventHandler()

            self.observer.schedule(event_handler, path=path, LocalPoller)
            self.observer.start()

            # notification
            if service[11]:
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(40001), 750, __icon__)).encode('utf-8',
                                                                                                                'ignore'))

    # episode: [int(tvdbid), int(tvdbepid), int(playcount), showtitle, epname, downloaded]
    # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
    def _service_betaserie(self, episode, service):
        utils.log(__addonname__ + "=> Main._service_betaserie")
        tstamp = int(time.time())
        # don't proceed if we had an authentication failure
        if not service[7]:
            # test if we are authenticated
            if not service[5]:
                # authenticate
                service = self._service_authenticate(service, str(tstamp))
            # only proceed if authentication was succesful
            if service[5]:
                # mark if we still have a valid session key after submission and have episode info
                if episode[0] and episode[1]:
                    service = self._service_mark_as_downloaded(service, episode)

    # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
    def _service_authenticate(self, service, timestamp):
        utils.log(__addonname__ + "=> Main._service_authenticate")
        # don't proceed if timeout timer has not expired
        if service[9] > int(timestamp):
            return service
        # create a pass hash
        md5pass = hashlib.md5()
        md5pass.update(service[4])
        url = service[1] + '/members/auth'
        urldata = {'v': self.apiver, 'key': service[2], 'login': service[3], 'password': md5pass.hexdigest()}
        try:
            # authentication request
            response = get_urldata(url, urldata, "POST")
            # authentication response
            data = json.loads(response)
            utils.log(__addonname__ + "=> successfully authenticated")
        except:
            service = self._service_fail(service, True)
            xbmc.executebuiltin(
                (u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(40006), 750, __icon__)).encode('utf-8',
                                                                                                            'ignore'))
            utils.log(__addonname__ + "=> failed to connect for authentication", xbmc.LOGNOTICE)
            return service
        # parse results
        if 'token' in data:
            # get token
            service[5] = str(data['token'])
            # reset failure count
            service[7] = 0
            # reset timer
            service[8] = 0
            service[9] = 0
        if data['errors']:
            utils.log(__addonname__ + "=> %s error %s : %s" % (
                service[0], data['errors'][0]['code'], data['errors'][0]['text']), xbmc.LOGNOTICE)
            if data['errors'][0]['code'] < 2000:
                # API error
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(40005), 750, __icon__)).encode('utf-8',
                                                                                                                'ignore'))
                utils.log(__addonname__ + "=> bad API usage", xbmc.LOGNOTICE)
                # disable the service, the monitor class will pick up the changes
                __addon__.setSetting('betaactive', 'false')
            elif data['errors'][0]['code'] > 4001:
                # login error
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(40007), 750, __icon__)).encode('utf-8',
                                                                                                                'ignore'))
                utils.log(__addonname__ + "=> login or password incorrect", xbmc.LOGNOTICE)
                service[6] = True
            else:
                # everything else
                service = self._service_fail(service, True)
                xbmc.executebuiltin(
                    (u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(40004), 750, __icon__)).encode('utf-8',
                                                                                                                'ignore'))
                utils.log(__addonname__ + "=> server error while authenticating", xbmc.LOGNOTICE)
        return service

    # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
    # episode: [int(tvdbid), int(tvdbepid), int(playcount), showtitle, epname, downloaded, showadded]
    def _service_mark_as_downloaded(self, service, episode):
        utils.log(__addonname__ + "=> ******IN _service_mark_as_downloaded *******", xbmc.LOGNOTICE)
        utils.log(__addonname__ + "=> service: " + str(service).strip('[]'), xbmc.LOGDEBUG)
        utils.log(__addonname__ + "=> episode: " + str(episode).strip('[]'), xbmc.LOGDEBUG)
        # episode not already marked as downloaded
        if not episode[5]:
            utils.log(__addonname__ + "=> Mark show as followed: %s, Show already added: %s" %
                     (str(service[10]), str(episode[6])), xbmc.LOGDEBUG)
            # want to add the show to the account and the show is not already added
            if service[10] and not episode[6]:
                url = service[1] + "/shows/show"
                urldata = {'v': self.apiver, 'key': service[2], 'token': service[5], 'thetvdb_id': episode[0]}
                try:
                    # marking request
                    response = get_urldata(url, urldata, "POST")
                    # marking response
                    data = json.loads(response)
                except:
                    service = self._service_fail(service, False)
                    utils.log(__addonname__ + "=> failed to follow show %s" % episode[3], xbmc.LOGNOTICE)
                    return service
                # parse results
                if data['errors']:
                    utils.log(__addonname__ + "=> %s error : %s %s" % (
                        service[0], data['errors'][0]['code'], (data['errors'][0]['text']).encode('utf-8', 'ignore')),
                             xbmc.LOGNOTICE)

                    if data['errors'][0]['code'] == 2001:
                        # drop our session key
                        service[6] = ''
                        utils.log(__addonname__ + "=> bad token while following show", xbmc.LOGNOTICE)
                        return service
                    elif data['errors'][0]['code'] == 2003:
                        utils.log(__addonname__ + "=> already following show %s" % episode[3])
                    else:
                        xbmc.executebuiltin((u'Notification(%s,%s,%s,%s)' % (
                            __addonname__, __language__(40008) + episode[3].decode('utf-8'), 750, __icon__)).encode(
                            'utf-8',
                            'ignore'))
                        utils.log(__addonname__ + "=> failed to follow show %s" % episode[3], xbmc.LOGNOTICE)
                        return service
                else:
                    if service[11]:
                        xbmc.executebuiltin((u'Notification(%s,%s,%s,%s)' % (
                            __addonname__, __language__(40002) + episode[3].decode('utf-8'), 750, __icon__)).encode(
                            'utf-8',
                            'ignore'))
                    utils.log(__addonname__ + "=> now following show %s" % (episode[3]))
            # mark episode as downloaded
            url = service[1] + "/episodes/downloaded"
            urldata = {'v': self.apiver, 'key': service[2], 'token': service[5], 'thetvdb_id': episode[1]}
            try:
                # marking request
                response = get_urldata(url, urldata, "POST")
                # marking response
                data = json.loads(response)
            except:
                service = self._service_fail(service, False)
                utils.log(__addonname__ + "=> failed to mark as downloaded", xbmc.LOGNOTICE)
                return service

            # parse results
            if data['errors']:
                utils.log(__addonname__ + "=> %s error : %s %s" % (
                    service[0], data['errors'][0]['code'], data['errors'][0]['text']),
                         xbmc.LOGNOTICE)
                if data['errors'][0]['code'] == 2001:
                    # drop our session key
                    service[6] = ''
                    utils.log(__addonname__ + "=> bad token while marking episode", xbmc.LOGNOTICE)
                elif data['errors'][0]['code'] == 0:
                    utils.log(
                        __addonname__ + "=> not following show, or episode %s already marked as downloaded" % episode[
                            5],
                        xbmc.LOGNOTICE)
                else:
                    xbmc.executebuiltin(
                        (u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(40009), 750, __icon__)).encode(
                            'utf-8',
                            'ignore'))
                    utils.log(__addonname__ + "=> error marking episode %s as downloaded" % episode[5], xbmc.LOGNOTICE)
            else:
                if service[11]:
                    xbmc.executebuiltin(
                        (u'Notification(%s,%s,%s,%s)' % (
                            __addonname__, __language__(40003), 750, __icon__)).encode(
                            'utf-8', 'ignore'))
                utils.log(__addonname__ + "=> %s episode %s marked as downloaded" % (episode[4], episode[5]))
            return service

    # [service, api-url, api-key, user, pass, token, auth-fail, failurecount, timercounter, timerexpiretime, follow, notify]
    def _service_fail(self, service, timer):
        timestamp = int(time.time())
        # increment failure counter
        service[7] += 1
        # drop our session key if we encouter three failures
        if service[7] > 2:
            service[5] = ''
        # set a timer if failure occurred during authentication phase
        if timer:
            # wrap timer if we cycled through all timeout values
            if service[8] == 0 or service[8] == 7680:
                service[8] = 60
            else:
                # increment timer
                service[8] *= 2
        # set timer expire time
        service[9] = timestamp + service[8]
        return service

        # tvShowsJSON = xbmc.executeJSONRPC(
        # '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": { "filter": {"field": "playcount", "operator": "is", "value": "0"}, "limits": { "start" : 0, "end": 75 }, "properties": ["art", "genre", "plot", "title", "originaltitle", "year", "rating", "thumbnail", "playcount", "file", "fanart"], "sort": { "order": "ascending", "method": "label" } }, "id": "libTvShows"}')
        # utils.log(tvShowsJSON)
        # tvShowsList = json.loads(tvShowsJSON)
        #
        # for tvShow in tvShowsList["result"]["tvshows"]:
        # episodesJSON = xbmc.executeJSONRPC(
        # '{"jsonrpc":"2.0","method":"VideoLibrary.GetEpisodes","id":1,"params":{"filter":{"field":"playcount", "operator":"is","value":"0"}, "properties":["season","episode","runtime","resume","playcount","tvshowid","lastplayed","file"],"tvshowid":' + str(
        #             tvShow["tvshowid"]) + ',"sort":{"order":"ascending","method":"lastplayed"}}}')
        #     utils.log(episodesJSON)
        #     episodesList = json.loads(episodesJSON)
        #
        #     for episode in episodesList["result"]["episodes"]:
        #         utils.log(str(episode["episode"]))

class EventHandler(FileSystemEventHandler):
    def on_created(self, event):
        utils.log('********* NOUVEAU FICHIER')

class MyVideoLibrary(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        utils.log(__addonname__ + "=> MyVideoLibrary.__init__")
        xbmc.Monitor.__init__(self)
        self.action = kwargs['action']
        self.service = kwargs['service']

    def onNotification(self, sender, method, data):
        utils.log(__addonname__ + "=> MyVideoLibrary.onNotification")
        if sender == 'xbmc':
            if method == 'VideoLibrary.OnUpdate':
                # if method == 'VideoLibrary.OnScanFinished':
                result = json.loads(data)
                utils.log(__addonname__ + "=> " + data)
                if 'item' in result and result['item']['type'] == 'episode':
                    if 'playcount' in result:
                        playcount = result['playcount']
                    else:
                        playcount = 0

                    episode = self._get_info(result['item']['id'], playcount)
                    if episode:
                        self.action(episode, self.service)

    def _get_info(self, episodeid, playcount):
        utils.log(__addonname__ + "=> IN ***** MyVideoLibrary._get_info *****")
        try:
            utils.log(__addonname__ + "=> Try to get infos from library", xbmc.LOGDEBUG)

            tvshow_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"episodeid": ' + str(
                episodeid) + ', "properties": ["tvshowid", "showtitle", "season", "episode"]}, "id": 1}'
            tvshow = json.loads(xbmc.executeJSONRPC(tvshow_query))['result']['episodedetails']
            tvdbid_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(
                tvshow['tvshowid']) + ', "properties": ["imdbnumber"]}, "id": 1}'
            tvdbid = json.loads(xbmc.executeJSONRPC(tvdbid_query))['result']['tvshowdetails']['imdbnumber']
            showtitle = tvshow['showtitle'].encode("utf-8")
            epname = str(tvshow['season']) + 'x' + str(tvshow['episode'])

            utils.log(__addonname__ + "=> Infos got from library, epname: " + epname, xbmc.LOGDEBUG)
        except:
            utils.log(__addonname__ + "=> could not get tvshow/episode details", xbmc.LOGNOTICE)
        if not tvdbid:
            utils.log(__addonname__ + "=> No tvdbid", xbmc.LOGDEBUG)

            url = self.service[1] + '/shows/search'
            urldata = '?v=2.4&key=' + self.service[2] + '&title=' + showtitle
            try:
                utils.log(__addonname__ + "=> Try to get infos from betaseries", xbmc.LOGDEBUG)

                tvdbid_query = get_urldata(url + urldata, '', "GET")
                tvdbid_query = json.loads(tvdbid_query)
                tvdbid = tvdbid_query['shows'][0]['thetvdb_id']

                utils.log(__addonname__ + "=> Infos got from betaseries " + tvdbid, xbmc.LOGDEBUG)
            except:
                utils.log(__addonname__ + "=> could not fetch tvshow's thetvdb_id", xbmc.LOGNOTICE)
                return False

        url = self.service[1] + '/shows/search'
        urldata = '?v=2.4&key=' + self.service[2] + '&title=' + showtitle
        try:
            utils.log(__addonname__ + "=> Try to get show informations from betaseries " + tvdbid, xbmc.LOGDEBUG)
            tvdbid_query = get_urldata(url + urldata, '', "GET")
            utils.log(__addonname__ + "=> " + tvdbid_query, xbmc.LOGDEBUG)
            tvdbid_query = json.loads(tvdbid_query)
            tvdbid = tvdbid_query['shows'][0]['thetvdb_id']
            showAdded = tvdbid_query['shows'][0]['in_account']
        except:
            utils.log(__addonname__ + "=> could not fetch tvshow's thetvdb_id", xbmc.LOGNOTICE)
            return False
        url = self.service[1] + '/shows/episodes'
        urldata = '?v=2.4&key=' + self.service[2] + '&thetvdb_id=' + str(tvdbid) + '&season=' + str(
            tvshow['season']) + '&episode=' + str(tvshow['episode'])
        try:
            tvdbepid_query = get_urldata(url + urldata, '', "GET")
            tvdbepid_query = json.loads(tvdbepid_query)
            tvdbepid = tvdbepid_query['episodes'][0]['thetvdb_id']
            downloaded = tvdbepid_query['episodes'][0]['user']['downloaded']
            showtitle = tvdbepid_query['episodes'][0]['title']
        except:
            utils.log(__addonname__ + "=> could not fetch episode's thetvdb_id | " + url + urldata, xbmc.LOGNOTICE)
            return False

        epinfo = [int(tvdbid), int(tvdbepid), int(playcount), showtitle, epname, downloaded, showAdded]

        utils.log(__addonname__ + "=> OUT ***** MyVideoLibrary._get_info *****")
        return epinfo


# monitor settings change
class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.action = kwargs['action']

    def onSettingsChanged(self):
        utils.log(__addonname__ + "=> onSettingsChanged")
        self.action()


utils.log('script started')
__useragent__ = set_user_agent()
Main()
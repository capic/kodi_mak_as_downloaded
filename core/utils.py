# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from fileinput import filename

import os
import re
import sys
import xbmc
import json
import settings
import urllib, urllib2, socket, hashlib, time, platform
import simplejson as json
from urllib import unquote
from threading import Condition


def log(msg, level=xbmc.LOGDEBUG):
    import settings

    xbmc.log(("[" + settings.ADDON_ID + "] " + msg).encode('utf-8', 'replace'), level)


def encode_path(path):
    """os.path does not handle unicode properly, i.e. when locale is C, file
    system encoding is assumed to be ascii. """
    if sys.platform.startswith('win'):
        return path
    return path.encode('utf-8')


def decode_path(path):
    if sys.platform.startswith('win'):
        return path
    return path.decode('utf-8')


def is_url(path):
    return re.match(r'^[A-z]+://', path) is not None


def escape_param(s):
    escaped = s.replace('\\', '\\\\').replace('"', '\\"')
    return '"' + escaped + '"'


def rpc(method, **params):
    params = json.dumps(params, encoding='utf-8')
    query = b'{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (method, params)
    return json.loads(xbmc.executeJSONRPC(query), encoding='utf-8')


def _split_multipaths(paths):
    ret = []
    for path in paths:
        if path.startswith("multipath://"):
            subpaths = path.split("multipath://")[1].split('/')
            subpaths = [unquote(path) for path in subpaths if path != ""]
            ret.extend(subpaths)
        else:
            ret.append(path)
    return ret


def get_media_sources(media_type):
    response = rpc('Files.GetSources', media=media_type)
    paths = [s['file'] for s in response.get('result', {}).get('sources', [])]
    paths = _split_multipaths(paths)
    return [path for path in paths if not path.startswith('upnp://')]


class OrderedSetQueue(object):
    """Queue with no repetition. Since we only have one consumer thread, this
    is simplified version."""

    def __init__(self):
        self.queue = []
        self.not_empty = Condition()

    def size(self):
        return len(self.queue)

    def put(self, item):
        self.not_empty.acquire()
        try:
            if item in self.queue:
                return
            self.queue.append(item)
            self.not_empty.notify()
        finally:
            self.not_empty.release()

    def get_nowait(self):
        self.not_empty.acquire()
        try:
            return self.queue.pop(0)
        finally:
            self.not_empty.release()

    def wait(self):
        """Wait for item to become available."""
        self.not_empty.acquire()
        try:
            while len(self.queue) == 0:
                self.not_empty.wait()
        finally:
            self.not_empty.release()


def set_user_agent():
    log(settings.LOG_ADDON_NAME + "set_user_agent", xbmc.LOGDEBUG)
    json_query = json.loads(xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }'))
    try:
        major = str(json_query['result']['version']['major'])
        minor = str(json_query['result']['version']['minor'])
        name = 'Kodi' if int(major) >= 14 else 'XBMC'
        version = "%s %s.%s" % (name, major, minor)
    except:
        log(settings.LOG_ADDON_NAME + "could not get app version", xbmc.LOGNOTICE)
        version = "XBMC"
    return "Mozilla/5.0 (compatible; " + settings.PLATFORM + "; " + version + "; " + settings.ADDON_ID + "/" + settings.ADDON_VERSION + ")"


def get_urldata(user_agent, url, urldata, method):
    log(settings.LOG_ADDON_NAME + "IN ***** get_urldata *****", xbmc.LOGDEBUG)

    log(settings.LOG_ADDON_NAME + "url: %s, urldata: %s, method: %s" % (url, urldata, method), xbmc.LOGDEBUG)

     # create a handler
    handler = urllib2.HTTPSHandler()
    # create an openerdirector instance
    opener = urllib2.build_opener(handler)

    if method == 'GET':
        url += '?'
        first = True
        for data in urldata:
            if not first:
                url += '&'
            url += data[0] + '=' + urllib.quote(str(data[1]))
            first = False
            log(settings.LOG_ADDON_NAME + "url building: %s" % url, xbmc.LOGDEBUG)
        body = ''
    else:
        # encode urldata
        body = urllib.urlencode(urldata)
    # build a request
    log(settings.LOG_ADDON_NAME + "url: %s" % url, xbmc.LOGDEBUG)
    req = urllib2.Request(url, data=body)
    # add any other information you want
    req.add_header('Accept', 'application/json')
    req.add_header('User-Agent', user_agent)
    # overload the get method function
    req.get_method = lambda: method
    try:
        # response = urllib2.urlopen(req)
        connection = opener.open(req)
    except urllib2.HTTPError as e:
        connection = e

    if connection.code:
        response = connection.read()
        log(settings.LOG_ADDON_NAME + "response : " + response, xbmc.LOGDEBUG)
        log(settings.LOG_ADDON_NAME + "OUT ***** OK get_urldata *****", xbmc.LOGDEBUG)
        return response
    else:
        log('response empty')

        log(settings.LOG_ADDON_NAME + "OUT ***** EMPTY get_urldata *****", xbmc.LOGDEBUG)
        return 0


def extract_shows_info_from_filename(filename_to_extract):
    log(settings.LOG_ADDON_NAME + "IN ***** extract_shows_info_from_filename *****", xbmc.LOGDEBUG)
    log(settings.LOG_ADDON_NAME + "filename_to_extract %s" % filename_to_extract, xbmc.LOGDEBUG)

    infos = []
    if filename_to_extract != "":
        infos_season_episode = re.search('S[0-9]+E[0-9]+', filename_to_extract, re.IGNORECASE)
        if infos_season_episode is not None:
            index_last_slash = filename_to_extract.rfind('/') + 1
            name = filename_to_extract[index_last_slash:]
            index_season_episode = name.index(infos_season_episode.group(0))
            season = re.search('S[0-9]+', name, re.IGNORECASE).group(0)[1:].lstrip('0')
            episode = re.search('E[0-9]+', name, re.IGNORECASE).group(0)[1:].lstrip('0')
            name = name[:index_season_episode]
            name = name.replace('.', ' ')
            name = name.replace('__', ':')
            name = name.strip()

            if name != "" and season != "" and episode != "":
                infos = [name, int(season), int(episode)]

    return infos

def extract_shows_info_from_directory_filename(filename_to_extract):
    log(settings.LOG_ADDON_NAME + "IN ***** extract_shows_info_from_directory_filename *****", xbmc.LOGDEBUG)
    log(settings.LOG_ADDON_NAME + "filename_to_extract %s" % filename_to_extract, xbmc.LOGDEBUG)

    infos = []
    if filename_to_extract != "":
        infos_season_episode = re.search('S[0-9]+E[0-9]+', filename_to_extract, re.IGNORECASE)
        if infos_season_episode is not None:
            index_last_slash = filename_to_extract.rfind('/') + 1
            show_name = filename_to_extract[index_last_slash:]
            directory = filename_to_extract[:index_last_slash - 1]
            index_last_slash = directory.rfind('/') + 1
            name = directory[index_last_slash:]
            season = re.search('S[0-9]+', show_name, re.IGNORECASE).group(0)[1:].lstrip('0')
            episode = re.search('E[0-9]+', show_name, re.IGNORECASE).group(0)[1:].lstrip('0')

            if name != "" and season != "" and episode != "":
                name = name.replace('__', ':')
                infos = [name.lower(), int(season), int(episode)]
                log(settings.LOG_ADDON_NAME + "%s" % infos, xbmc.LOGDEBUG)

    log(settings.LOG_ADDON_NAME + "OUT ***** extract_shows_info_from_directory_filename *****", xbmc.LOGDEBUG)

    return infos
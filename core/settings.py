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

import xbmcaddon
import utils
import platform

ADDON = xbmcaddon.Addon()
ADDON_TRAD = ADDON.getLocalizedString
ADDON_ID = ADDON.getAddonInfo('id').decode('utf-8')
ADDON_VERSION = ADDON.getAddonInfo('version').decode('utf-8')
ADDON_NAME = ADDON.getAddonInfo('name').decode('utf-8')
ADDON_ICON = ADDON.getAddonInfo('icon')
LOG_ADDON_NAME = "[ ** " + ADDON_NAME + " ** ] => "

BETA_ACTIVE = ADDON.getSetting('betaactive') == 'true'
BETA_USER = ADDON.getSetting('betauser')
BETA_PASS = ADDON.getSetting('betapass')
BETA_FOLLOW = ADDON.getSetting('betafollow') == 'true'
BETA_NOTIFY = ADDON.getSetting('betanotify') == 'true'

SCAN_ON_START = ADDON.getSetting('scanonstart') == 'true'
SHOW_PROGRESS_DIALOG = ADDON.getSetting('hideprogress') == 'false'
SHOW_STATUS_DIALOG = ADDON.getSetting('showstatusdialog') == 'true'

# POLLING = int(ADDON.getSetting('method'))
# PER_FILE_REMOVE = int(ADDON.getSetting('removalmethod')) == 1
POLLING_INTERVAL = int("0"+ADDON.getSetting('pollinginterval')) or 4
RECURSIVE = ADDON.getSetting('recursivepolling') == 'true'
# SCAN_DELAY = int("0"+ADDON.getSetting('delay')) or 1
STARTUP_DELAY = int("0"+ADDON.getSetting('startupdelay'))
# FORCE_GLOBAL_SCAN = ADDON.getSetting('forceglobalscan') == 'true'

PLATFORM = platform.system() + " " + platform.release()
API_KEY = '5a85a0adc953'
API_URL = 'https://api.betaseries.com'
API_VER = '2.4'

if ADDON.getSetting('watchvideo') == 'true':
    VIDEO_SOURCES = utils.get_media_sources('video')
else:
    VIDEO_SOURCES = [_ for _ in set([
        ADDON.getSetting('videosource1').decode('utf-8'),
        ADDON.getSetting('videosource2').decode('utf-8'),
        ADDON.getSetting('videosource3').decode('utf-8'),
        ADDON.getSetting('videosource4').decode('utf-8'),
        ADDON.getSetting('videosource5').decode('utf-8')]) if _ != ""]

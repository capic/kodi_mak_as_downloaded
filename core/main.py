from __future__ import unicode_literals

import os
import traceback
import xbmc
import xbmcvfs
import xbmcgui
import utils
import settings
import time
import emitters
from betaseries import BetaSeriesDownloaded
from utils import escape_param, set_user_agent
from itertools import repeat
from watchdog.events import FileSystemEventHandler
from watchdog.utils.compat import Event
from emitters import MultiEmitterObserver
from polling_local import _Recursive


class EventHandler(FileSystemEventHandler):
    """
    Handles raw incoming events for single root path and library,
    and queues scan/clean commands to the xbmcif singleton.
    """

    def __init__(self, library, path, betaSeriesDownloaded):
        FileSystemEventHandler.__init__(self)
        self.library = library
        self.path = path
        self.supported_media = '|' + xbmc.getSupportedMedia(library).decode('utf-8') + '|'
        self.betaSeriesDownloaded = betaSeriesDownloaded

    def on_created(self, event):
        # if not event.is_directory and not self._can_skip(event, event.src_path):
        file = utils.extract_shows_info_from_directory_filename(event.src_path)
        self.betaSeriesDownloaded._service_betaserie(file)

    def on_any_event(self, event):
        xbmc.log(settings.LOG_ADDON_NAME + "[event] <%s> <%r>" % (event.event_type, event.src_path), xbmc.LOGDEBUG)

    def _is_hidden(self, path):
        sep = '/' if utils.is_url(self.path) else os.sep
        relpath = path[len(self.path):] if path.startswith(self.path) else path
        for part in relpath.split(sep):
            if part.startswith('.') or part.startswith('_UNPACK'):
                return True
        return False

    def _can_skip(self, event, path):
        if not path:
            return False
        if self._is_hidden(path):
            xbmc.log(settings.LOG_ADDON_NAME + "[event] skipping <%s> <%r>" % (event.event_type, path), xbmc.LOGDEBUG)
            return True
        if not event.is_directory:
            _, ext = os.path.splitext(path)
            ext = ext.lower()
            if self.supported_media.find('|%s|' % ext) == -1:
                xbmc.log(settings.LOG_ADDON_NAME + "[event] skipping <%s> <%r>" % (event.event_type, path),
                         xbmc.LOGDEBUG)
                return True
        return False


def prepare_files(directory, files_to_scan, episode_to_download_in_account):
    xbmc.log(settings.LOG_ADDON_NAME + "*** IN prepare_files", xbmc.LOGDEBUG)
    xbmc.log(settings.LOG_ADDON_NAME + "Scan directory %s" % directory, xbmc.LOGDEBUG)

    dirs, files = xbmcvfs.listdir(directory)

    for file in files:
        ext = file[file.rfind('.') + 1:]

        if ext == 'mkv' or ext == 'avi':
            file_infos = utils.extract_shows_info_from_directory_filename(directory + "/" + file)

            if len(file_infos) > 0 and len(episode_to_download_in_account) > 0:
                try:
                    xbmc.log(settings.LOG_ADDON_NAME + "Show %s exists in account ?" % file_infos[0], xbmc.LOGDEBUG)
                    if file_infos[0] in episode_to_download_in_account.keys():
                        xbmc.log(settings.LOG_ADDON_NAME + "Yes", xbmc.LOGDEBUG)
                        xbmc.log(settings.LOG_ADDON_NAME + "Season %s exists in account ?" % file_infos[1],
                                 xbmc.LOGDEBUG)
                        if file_infos[1] in episode_to_download_in_account[file_infos[0]].keys():
                            xbmc.log(settings.LOG_ADDON_NAME + "Yes", xbmc.LOGDEBUG)
                            xbmc.log(settings.LOG_ADDON_NAME + "Episode %s exists in account ?" % file_infos[2],
                                     xbmc.LOGDEBUG)
                            if file_infos[2] not in episode_to_download_in_account[file_infos[0]][file_infos[1]]:
                                xbmc.log(settings.LOG_ADDON_NAME + "No: add to mark as downloaded", xbmc.LOGDEBUG)
                                files_to_scan.append(file_infos)
                            else:
                                xbmc.log(settings.LOG_ADDON_NAME + "Yes: not to be marked as downloaded", xbmc.LOGDEBUG)
                        else:
                            xbmc.log(settings.LOG_ADDON_NAME + "No: add to mark as downloaded", xbmc.LOGDEBUG)
                            files_to_scan.append(file_infos)
                    else:
                        xbmc.log(settings.LOG_ADDON_NAME + "No: add to mark as downloaded", xbmc.LOGDEBUG)
                        files_to_scan.append(file_infos)
                except:
                    raise
                    # else:
                    # files_to_scan.append(file_infos)

    for dir in dirs:
        prepare_files(directory + dir, files_to_scan, episode_to_download_in_account)

    xbmc.log(settings.LOG_ADDON_NAME + "*** OUT prepare_files", xbmc.LOGDEBUG)

    return files_to_scan


# def scan_on_start(directories, betaseries_downloaded, progress):
# files_to_scan = []
#
# for directory in directories:
# files_to_scan.append(prepare_files(directory, files_to_scan))
#
#     xbmc.log(settings.LOG_ADDON_NAME + "-------- %s files to mark as downloaded : %s" % (str(len(files_to_scan)), files_to_scan), xbmc.LOGDEBUG)
#
#     i = 0
#     for file in files_to_scan:
#         progress.update(i / len(files_to_scan) * 100, message="File %s" % file)
#         betaseries_downloaded._service_betaserie(file)
#         i += 1


def main():
    progress = xbmcgui.DialogProgressBG()
    progress.create("BetaSeries Downloaded starting. Please wait...")

    if settings.STARTUP_DELAY > 0:
        xbmc.log(settings.LOG_ADDON_NAME + "waiting for user delay of %d seconds" % settings.STARTUP_DELAY,
                 xbmc.LOGDEBUG)
        msg = "Delaying startup by %d seconds."
        progress.update(0, message=msg % settings.STARTUP_DELAY)
        start = time.time()
        while time.time() - start < settings.STARTUP_DELAY:
            xbmc.sleep(100)
            if xbmc.abortRequested:
                progress.close()
                return

    if settings.BETA_ACTIVE and settings.BETA_USER and settings.BETA_PASS:
        sources = []
        video_sources = settings.VIDEO_SOURCES
        sources.extend(zip(repeat('video'), video_sources))
        xbmc.log("video sources %s" % video_sources, xbmc.LOGDEBUG)

        beta_series_downloaded = BetaSeriesDownloaded(__useragent__)

        if settings.SCAN_ON_START:
            xbmc.log(settings.LOG_ADDON_NAME + "scan on start", xbmc.LOGDEBUG)

            # get the list of  episodes already in
            progress.update(0, message="Get the list of episodes from BetaSeries")
            episode_to_download_in_account = beta_series_downloaded._get_episode_already_in_account()

            xbmc.log(settings.LOG_ADDON_NAME + "-------- list files in account%s (%s)" % (
                episode_to_download_in_account, len(episode_to_download_in_account)),
                     xbmc.LOGDEBUG)
            files_to_scan = []
            progress.close()
            progress.create("Prepare files to mark as download. Please wait...")
            for directory in settings.VIDEO_SOURCES:
                files_to_scan = prepare_files(directory + "/", files_to_scan, episode_to_download_in_account)

            xbmc.log(settings.LOG_ADDON_NAME + "-------- list files %s (%s)" % (files_to_scan, len(files_to_scan)),
                     xbmc.LOGNOTICE)

            progress_count = 0.
            files_to_scan_len = len(files_to_scan)
            progress.close()
            progress.create("Check list of files. Please wait...")
            for file in files_to_scan:
                progress_calc = progress_count / files_to_scan_len
                xbmc.log(
                    settings.LOG_ADDON_NAME + "progress_count = %s, len(files_to_scan) = %s, progress_calc = %s" % (
                        progress_count, len(files_to_scan), progress_calc),
                    xbmc.LOGDEBUG)
                progress.update(int(progress_calc * 100), message="Scan %s" % file)
                beta_series_downloaded._service_betaserie(file)
                progress_count += 1.

        observer = MultiEmitterObserver()
        observer.start()  # start so emitters are started on schedule

        for i, (libtype, path) in enumerate(sources):
            progress.update((i + 1) / len(sources) * 100, message="Setting up %s" % path)
            try:
                emitter_cls = emitters.select_emitter(path)
            except IOError:
                xbmc.log("not watching <%s>. does not exist" % path, xbmc.LOGNOTICE)
                continue
            finally:
                if xbmc.abortRequested:
                    break

            eh = EventHandler(libtype, path, beta_series_downloaded)
            try:
                observer.schedule(eh, path=path, emitter_cls=emitter_cls)
                xbmc.log("watching <%s> using %s" % (path, emitter_cls), xbmc.LOGNOTICE)
            except Exception:
                traceback.print_exc()
                xbmc.log("failed to watch <%s>" % path, xbmc.LOGNOTICE)
            finally:
                if xbmc.abortRequested:
                    break

        progress.close()
        xbmc.log("initialization done", xbmc.LOGDEBUG)

        if settings.SHOW_STATUS_DIALOG:
            watching = ["Watching '%s'" % path for _, path in sources
                        if path in observer.paths]
            not_watching = ["Not watching '%s'" % path for _, path in sources
                            if path not in observer.paths]
            dialog = xbmcgui.Dialog()
            dialog.select('Watchdog status', watching + not_watching)

        if xbmc.__version__ >= '2.19.0':
            monitor = xbmc.Monitor()
            monitor.waitForAbort()
        else:
            while not xbmc.abortRequested:
                xbmc.sleep(100)

        xbmc.log("stopping..", xbmc.LOGDEBUG)
        observer.stop()
        observer.join()


__useragent__ = set_user_agent()
if __name__ == "__main__":
    main()

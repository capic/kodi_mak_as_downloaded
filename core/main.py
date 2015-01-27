from __future__ import unicode_literals

import os
import traceback
import xbmc
import xbmcgui
import utils
import settings
import emitters
from betaseries import BetaSeriesDownloaded
from utils import escape_param, set_user_agent
from itertools import repeat
from watchdog.events import FileSystemEventHandler
from watchdog.utils.compat import Event
from emitters import MultiEmitterObserver


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
        self.betaSeriesDownloaded._service_betaserie(event.src_path)

    def on_any_event(self, event):
        xbmc.log("[event] <%s> <%r>" % (event.event_type, event.src_path))

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
            log("[event] skipping <%s> <%r>" % (event.event_type, path))
            return True
        if not event.is_directory:
            _, ext = os.path.splitext(path)
            ext = ext.lower()
            if self.supported_media.find('|%s|' % ext) == -1:
                log("[event] skipping <%s> <%r>" % (event.event_type, path))
                return True
        return False


def main():
    progress = xbmcgui.DialogProgressBG()
    progress.create("BetaSeries Downloaded starting. Please wait...")

    if settings.STARTUP_DELAY > 0:
        xbmc.log(settings.LOG_ADDON_NAME + "waiting for user delay of %d seconds" % settings.STARTUP_DELAY)
        msg = "Delaying startup by %d seconds."
        progress.update(0, message=msg % settings.STARTUP_DELAY)
        start = time.time()
        while time.time() - start < settings.STARTUP_DELAY:
            xbmc.sleep(100)
            if xbmc.abortRequested:
                progress.close()
                return

    if settings.BETA_ACTIVE and settings.BETA_USER and settings.BETA_PASS:
        xbmc.log(settings.LOG_ADDON_NAME + "betaactive and betauser and betapass")

        sources = []
        video_sources = settings.VIDEO_SOURCES
        sources.extend(zip(repeat('video'), video_sources))
        xbmc.log("video sources %s" % video_sources)

        betaSeriesDownloaded = BetaSeriesDownloaded(__useragent__)

        # if settings.SCAN_ON_START:


        observer = MultiEmitterObserver()
        observer.start()  # start so emitters are started on schedule

        for i, (libtype, path) in enumerate(sources):
            progress.update((i + 1) / len(sources) * 100, message="Setting up %s" % path)
            try:
                emitter_cls = emitters.select_emitter(path)
            except IOError:
                xbmc.log("not watching <%s>. does not exist" % path)
                continue
            finally:
                if xbmc.abortRequested:
                    break

            eh = EventHandler(libtype, path, betaSeriesDownloaded)
            try:
                observer.schedule(eh, path=path, emitter_cls=emitter_cls)
                xbmc.log("watching <%s> using %s" % (path, emitter_cls))
            except Exception:
                traceback.print_exc()
                xbmc.log("failed to watch <%s>" % path)
            finally:
                if xbmc.abortRequested:
                    break

        progress.close()
        xbmc.log("initialization done")

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

        xbmc.log("stopping..")
        observer.stop()
        observer.join()


__useragent__ = set_user_agent()
if __name__ == "__main__":
    main()

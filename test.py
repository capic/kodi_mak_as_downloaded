import xbmcvfs

dirs, files = xbmcvfs.listdir('smb://DLINK-CAPIC/Volume_1/Media/Videos/A REGARDER PLUS TARD/')
print(dirs)
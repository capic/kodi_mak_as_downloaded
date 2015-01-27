import re

def extract_shows_info_from_filename(filenametoextract):
    infos = []
    if filenametoextract != "":
        infosseasonepisode = re.search('S[0-9]+E[0-9]+', filenametoextract)

        if infosseasonepisode != "":
            indexseasonepisode = filenametoextract.index(infosseasonepisode.group(0))

            season = re.search('S[0-9]+', filenametoextract).group(0)[1:]
            episode = re.search('E[0-9]+', filenametoextract).group(0)[1:]
            name = filenametoextract[:indexseasonepisode].replace('.', ' ')

            if name != "" and season != "" and episode != "":
                infos = [name, season, episode]

    return infos

infos = extract_shows_info_from_filename('A.to.Z.S01E02.720p.HDTV.X264-DIMENSION_www.theextopia.com')
print(infos[0])
print(infos[1])
print(infos[2])
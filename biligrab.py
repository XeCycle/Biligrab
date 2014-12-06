#!/usr/bin/env python
# coding:utf-8
# Author: Beining --<ACICFG>
# Purpose: Yet another danmaku and video file downloader of Bilibili.
# Created: 11/06/2013
# 
# Biligrab is licensed under MIT license
# 
# Copyright (c) 2013-2014

'''
Biligrab 0.98.3
Beining@ACICFG
cnbeining[at]gmail.com
http://www.cnbeining.com
https://github.com/cnbeining/Biligrab
MIT license
'''

import sys
import os
from StringIO import StringIO
import gzip
import urllib
import urllib2
import math
import json
import commands
import subprocess
import hashlib
import getopt
import logging
import traceback

from xml.dom.minidom import parse, parseString
import xml.dom.minidom

try:
    from danmaku2ass2 import *
except:
    pass

reload(sys)
sys.setdefaultencoding('utf-8')

global vid, cid, partname, title, videourl, part_now, is_first_run, APPKEY, SECRETKEY, LOG_LEVEL, VER, LOCATION_DIR, VIDEO_FORMAT, convert_ass, is_export, IS_SLIENT, pages, IS_M3U, FFPROBE_USABLE

cookies, VIDEO_FORMAT = '', ''
LOG_LEVEL, pages, FFPROBE_USABLE = 0, 0, 0
APPKEY = '85eb6835b0a1034e'
SECRETKEY = '2ad42749773c441109bdc0191257a664'
VER = '0.98.3'
FAKE_HEADER = {
    'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'}
LOCATION_DIR = os.getcwd()


#----------------------------------------------------------------------
def print_error(data):
    """str->None"""
    print('Dumping info...')
    print('=======================DUMP DATA==================')
    print(data)
    print('========================DATA END==================')

#----------------------------------------------------------------------
def list_del_repeat(list):
    """delete repeating items in a list, and keep the order.
    http://www.cnblogs.com/infim/archive/2011/03/10/1979615.html"""
    l2 = []
    [l2.append(i) for i in list if not i in l2]
    return(l2)

#----------------------------------------------------------------------
def calc_sign(string):
    """str/any->str
    return MD5."""
    return str(hashlib.md5(str(string).encode('utf-8')).hexdigest())

#----------------------------------------------------------------------
def read_cookie(cookiepath):
    """str->list
    Original target: set the cookie
    Target now: Set the global header"""
    global BILIGRAB_HEADER
    try:
        cookies_file = open(cookiepath, 'r')
        cookies = cookies_file.readlines()
        cookies_file.close()
        # print(cookies)
        return cookies
    except:
        print('WARNING: Cannot read cookie, may affect some videos...')
        return ['']

#----------------------------------------------------------------------
def clean_name(name):
    """str->str
    delete all the dramas in the filename."""
    return (str(name).strip().replace('\\',' ').replace('/', ' ').replace('&', ' ')).replace('-', ' ')

#----------------------------------------------------------------------
def mylist_to_aid_list(mylist):
    """str/int->list"""
    request = urllib2.Request('http://www.bilibili.com/mylist/mylist-{mylist}.js'.format(mylist = mylist), headers = FAKE_HEADER)
    response = urllib2.urlopen(request)
    aid_list = []
    data = response.read()
    for i in data.split('\n')[-3].split(','):
        if 'aid' in i:
            aid_list.append(i.split(':')[1])
    return aid_list

#----------------------------------------------------------------------
def find_cid_api(vid, p, cookies):
    """find cid and print video detail
    str,int?,str->str,str,str,str
    TODO: Use json."""
    global cid, partname, title, videourl, pages
    cid = 0
    title , partname , pages, = '', '', ''
    if str(p) is '0' or str(p) is '1':
        str2Hash = 'appkey={APPKEY}&id={vid}&type=xml{SECRETKEY}'.format(APPKEY = APPKEY, vid = vid, SECRETKEY = SECRETKEY)
        biliurl = 'https://api.bilibili.com/view?appkey={APPKEY}&id={vid}&type=xml&sign={sign}'.format(APPKEY = APPKEY, vid = vid, SECRETKEY = SECRETKEY, sign = calc_sign(str2Hash))
    else:
        str2Hash = 'appkey={APPKEY}&id={vid}&page={p}&type=xml{SECRETKEY}'.format(APPKEY = APPKEY, vid = vid, p = p, SECRETKEY = SECRETKEY)
        biliurl = 'https://api.bilibili.com/view?appkey={APPKEY}&id={vid}&page={p}&type=xml&sign={sign}'.format(APPKEY = APPKEY, vid = vid, SECRETKEY = SECRETKEY, p = p, sign = calc_sign(str2Hash))
    print('DEBUG: ' + biliurl)
    videourl = 'http://www.bilibili.com/video/av{vid}/index_{p}.html'.format(vid = vid, p = p)
    print('INFO: Fetching webpage...')
    try:
        request = urllib2.Request(biliurl, headers=BILIGRAB_HEADER)
        response = urllib2.urlopen(request)
        data = response.read()
        if LOG_LEVEL == 1:
            print_error(data)
        dom = parseString(data)
        for node in dom.getElementsByTagName('cid'):
            if node.parentNode.tagName == "info":
                cid = node.toxml()[5:-6]
                print('INFO: cid is ' + cid)
                break
        for node in dom.getElementsByTagName('partname'):
            if node.parentNode.tagName == "info":
                partname = clean_name(str(node.toxml()[10:-11]))
                print('INFO: partname is ' + partname)  # no more /\ drama
                break
        for node in dom.getElementsByTagName('title'):
            if node.parentNode.tagName == "info":
                title = clean_name(str(node.toxml()[7:-8]))
                print('INFO: Title is ' + title)
        for node in dom.getElementsByTagName('pages'):
            if node.parentNode.tagName == "info":
                pages = clean_name(str(node.toxml()[7:-8]))
                print('INFO: Total pages is ' + str(pages))
        return [cid, partname, title, pages]
    except:  # If API failed
        print(
            'WARNING: Cannot connect to API server! \nIf you think this is wrong, please open an issue at \nhttps://github.com/cnbeining/Biligrab/issues with *ALL* the screen output, \nas well as your IP address and basic system info.\nYou can get these data via "-l".')
        if LOG_LEVEL == 1:
            print_error(data)
        else:
            print('WARNING: Cannot connect to API server!')
        return ['', '', '', '']

#----------------------------------------------------------------------
def find_cid_flvcd(videourl):
    """str->None
    set cid."""
    global vid, cid, partname, title
    print('INFO: Fetching webpage via Flvcd...')
    request = urllib2.Request(videourl, headers=FAKE_HEADER)
    request.add_header('Accept-encoding', 'gzip')
    response = urllib2.urlopen(request)
    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(response.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    data_list = data.split('\n')
    if LOG_LEVEL == 1:
        print_error(data)
    # Todo: read title
    for lines in data_list:
        if 'cid=' in lines:
            cid = lines.split('&')
            cid = cid[0].split('=')
            cid = cid[-1]
            print('INFO: cid is ' + str(cid))
            break

#----------------------------------------------------------------------
def check_dependencies(download_software, concat_software, probe_software):
    """None->str,str,str
    Will give softwares for concat, download and probe.
    The detection of Python3 is located at the end of Main function."""
    concat_software_list = ['ffmpeg', 'avconv']
    download_software_list = ['aria2c', 'axel', 'wget', 'curl']
    probe_software_list = ['ffprobe', 'mediainfo']
    name_list = [[concat_software,
                  concat_software_list],
                 [download_software,
                  download_software_list],
                 [probe_software,
                  probe_software_list]]
    for name in name_list:
        if name[0].strip().lower() not in name[1]:  # Unsupported software
            # Set a Unsupported software,  not blank
            if len(name[0].strip()) != 0:
                print('WARNING: Requested Software not supported!\n         Biligrab only support these following software(s):\n         ' + str(name[1]) + '\n         Trying to find available one...')
            for software in name[1]:
                output = commands.getstatusoutput(software + ' --help')
                if str(output[0]) != '32512':  # If exist
                    name[0] = software
                    break
        if name[0] == '':
            print('FATAL: Cannot find software in ' + str(name[1]) + ' !')
            exit()
    return name_list[0][0], name_list[1][0], name_list[2][0]

#----------------------------------------------------------------------
def download_video(part_number, download_software, video_link):
    """"""
    if download_software == 'aria2c':
        cmd = 'aria2c -c -s16 -x16 -k1M --out {part_number}.flv "{video_link}"'
    elif download_software == 'wget':
        cmd = 'wget -c -O {part_number}.flv "{video_link}"'
    elif download_software == 'curl':
        cmd = 'curl -L -C -o {part_number}.flv "{video_link}"'
    elif download_software == 'axel':
        cmd = 'axel -n 20 -o {part_number}.flv "{video_link}"'
    os.system(cmd.format(part_number = part_number, video_link = video_link))

#----------------------------------------------------------------------
def concat_videos(concat_software, vid_num, filename):
    """str,str->None"""
    global VIDEO_FORMAT
    if concat_software == 'ffmpeg':
        f = open('ff.txt', 'w')
        ff = ''
        cwd = os.getcwd()
        for i in range(vid_num):
            ff = ff + 'file \'{cwd}/{i}.flv\'\n'.format(cwd = cwd, i = i)
        ff = ff.encode("utf8")
        f.write(ff)
        f.close()
        if LOG_LEVEL == 1:
            print_error(ff)
        print('INFO: Concating videos...')
        os.system('ffmpeg -f concat -i ff.txt -c copy "' + filename + '".mp4')
        VIDEO_FORMAT = 'mp4'
        if os.path.isfile(str(filename + '.mp4')):
            os.system('rm -r ff.txt')
            for i in range(vid_num):
                os.system('rm -r ' + str(i) + '.flv')
            print('INFO: Done, enjoy yourself!')
        else:
            print('ERROR: Cannot concatenative files, trying to make flv...')
            os.system('ffmpeg -f concat -i ff.txt -c copy "' + filename + '".flv')
            VIDEO_FORMAT = 'flv'
            if os.path.isfile(str(filename + '.flv')):
                print('WARNING: FLV file made. Not possible to mux to MP4, highly likely due to audio format.')
                os.system('rm -r ff.txt')
                for i in range(vid_num):
                    os.system('rm -r ' + str(i) + '.flv')
            else:
                print('ERROR: Cannot concatenative files!')
    elif concat_software == 'avconv':
        pass

#----------------------------------------------------------------------
def process_m3u8(url):
    """str->list
    Only Youku."""
    url_list = []
    request = urllib2.Request(url, headers=BILIGRAB_HEADER)
    try:
        response = urllib2.urlopen(request)
    except:
        print('ERROR: Cannot download required m3u8!')
        return []
    data = response.read()
    if LOG_LEVEL == 1:
        print_error(data)
    data = data.split()
    if 'youku' in url:
        return [data[4].split('?')[0]]

#----------------------------------------------------------------------
def make_m3u8(video_list):
    """list->str
    list:
    [(VIDEO_URL, TIME_IN_SEC), ...]"""
    TARGETDURATION = int(max([i[1] for i in video_list])) + 1
    line = '#EXTM3U\n#EXT-X-TARGETDURATION:{TARGETDURATION}\n#EXT-X-VERSION:2\n'.format(TARGETDURATION = TARGETDURATION)
    for i in video_list:
        line += '#EXTINF:{time}\n{url}\n'.format(time = str(i[1]), url = i[0])
    line += '#EXT-X-ENDLIST'
    return line

#----------------------------------------------------------------------
def find_video_address_html5(vid, p, header):
    """str,str,dict->list
    Method #3."""
    api_url = 'http://m.acg.tv/m/html5?aid={vid}&page={p}'.format(vid = vid, p = p)
    request = urllib2.Request(api_url, headers=header)
    url_list = []
    try:
        response = urllib2.urlopen(request)
    except:
        print('ERROR: Cannot connect to HTML5 API!')
        return []
    data = response.read()
    if LOG_LEVEL == 1:
        print_error(data)
    info = json.loads(data.decode('utf-8'))
    raw_url = info['src']
    if 'error.mp4' in raw_url:
        print('ERROR: HTML5 API returned ERROR or not avalable!')
        return []
    if 'm3u8' in raw_url:
        print('INFO: Found m3u8, processing...')
        return process_m3u8(raw_url)
    return [raw_url]

#----------------------------------------------------------------------
def find_video_address_force_original(cid, header):
    """str,str->str
    Give the original URL, if possible.
    Method #2."""
        # Force get oriurl
    sign_this = calc_sign('appkey={APPKEY}&cid={cid}{SECRETKEY}'.format(APPKEY = APPKEY, cid = cid, SECRETKEY = SECRETKEY))
    api_url = 'http://interface.bilibili.com/player?'
    request = urllib2.Request(api_url + 'appkey={APPKEY}&cid={cid}&sign={sign_this}'.format(APPKEY = APPKEY, cid = cid, SECRETKEY = SECRETKEY, sign_this = sign_this), headers=header)
    response = urllib2.urlopen(request)
    data = response.read()
    if LOG_LEVEL == 1:
        print_error(data)
    data = data.split('\n')
    for l in data:
        if 'oriurl' in l:
            originalurl = str(l[8:-9])
            print('INFO: Original URL is ' + originalurl)
            return originalurl
    print('WARNING: Cannot get original URL! Chances are it does not exist.')
    return ''

#----------------------------------------------------------------------
def find_link_flvcd(videourl):
    """str->list
    Used in method 2 and 5."""
    print('INFO: Finding link via Flvcd...')
    request = urllib2.Request('http://www.flvcd.com/parse.php?' +
                              urllib.urlencode([('kw', videourl)]), headers=FAKE_HEADER)
    request.add_header('Accept-encoding', 'gzip')
    response = urllib2.urlopen(request)
    data = response.read()
    data_list = data.split('\n')
    if LOG_LEVEL == 1:
        print_error(data)
    for items in data_list:
        if 'name' in items and 'inf' in items and 'input' in items:
            c = items
            rawurlflvcd = c[59:-5]
            rawurlflvcd = rawurlflvcd.split('|')
            return rawurlflvcd

#----------------------------------------------------------------------
def find_video_address_normal_api(cid, header, method, convert_m3u = False):
    """str,str,str->list
    Change in 0.98: Return the file list directly.
    Method:
    0: Original API
    1: CDN API
    2: Original URL API - Divided in another function
    3: Mobile API - Divided in another function
    4: Flvcd - Divided in another function
     [(VIDEO_URL, TIME_IN_SEC), ...]
    """
    sign_this = calc_sign('appkey={APPKEY}&cid={cid}{SECRETKEY}'.format(APPKEY = APPKEY, cid = cid, SECRETKEY = SECRETKEY))
    if method == '1':
        api_url = 'http://interface.bilibili.com/v_cdn_play?'
    else:  #Method 0 or other
        api_url = 'http://interface.bilibili.com/playurl?'
    request = urllib2.Request(api_url + 'appkey={APPKEY}&cid={cid}&sign={sign_this}'.format(APPKEY = APPKEY, cid = cid, SECRETKEY = SECRETKEY, sign_this = sign_this), headers=header)
    response = urllib2.urlopen(request)
    data = response.read()
    if LOG_LEVEL == 1:
        print_error(data)
    for l in data.split('\n'):  # In case shit happens
        if 'error.mp4' in l:
            logging.warning('API header may be blocked!')
            return ['API_BLOCKED']
    rawurl = []
    originalurl = ''
    dom = parseString(data)
    if convert_m3u:
        for node in dom.getElementsByTagName('durl'):
            length = node.getElementsByTagName('length')[0]
            url = node.getElementsByTagName('url')[0]
            rawurl.append((url.childNodes[0].data, int(int(length.childNodes[0].data) / 1000) + 1))
    else:
        for node in dom.getElementsByTagName('durl'):
            url = node.getElementsByTagName('url')[0]
            rawurl.append(url.childNodes[0].data)
    return rawurl

#----------------------------------------------------------------------
def get_video(oversea, convert_m3u = False):
    """str->list
    A full parser for getting video.
    convert_m3u: [(URL, time_in_sec)]
    else: [url,url]"""
    rawurl = []
    if oversea == '2':
        raw_link = find_video_address_force_original(cid, BILIGRAB_HEADER)
        rawurl = find_link_flvcd(raw_link)
    elif oversea == '3':
        rawurl = find_video_address_html5(vid, p, BILIGRAB_HEADER)
    elif oversea == '4':
        rawurl = find_link_flvcd(videourl)
    else:
        rawurl = find_video_address_normal_api(cid, BILIGRAB_HEADER, oversea, convert_m3u)
        if 'API_BLOCKED' in rawurl[0]:
            print('WARNING: API header may be blocked! Using fake one instead...')
            rawurl = find_video_address_normal_api(cid, FAKE_HEADER, oversea, convert_m3u)
    return rawurl

#----------------------------------------------------------------------
def get_resolution(filename, probe_software):
    """str,str->list"""
    resolution = []
    filename = filename + '.' + VIDEO_FORMAT
    try:
        if probe_software == 'mediainfo':
            resolution = get_resolution_mediainfo(filename)
        if probe_software == 'ffprobe':
            resolution = get_resolution_ffprobe(filename)
        if LOG_LEVEL == 1:
            print('DEBUG: Software: {probe_software}, resolution {resolution}'.format(probe_software = probe_software, resolution = resolution))
        return resolution
    except:  # magic number
        return[1280, 720]

#----------------------------------------------------------------------
def get_resolution_mediainfo(filename):
    """str->list
    [640,360]
    path to dimention"""
    resolution = str(os.popen('mediainfo \'--Inform=Video;%Width%x%Height%\' "' +filename +'"').read()).strip().split('x')
    return [int(resolution[0]), int(resolution[1])]

#----------------------------------------------------------------------
def get_resolution_ffprobe(filename):
    '''str->list
    [640,360]'''
    width = ''
    height = ''
    cmnd = [
        'ffprobe',
        '-show_format',
        '-show_streams',
        '-pretty',
        '-loglevel',
        'quiet',
        filename]
    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # print filename
    out, err = p.communicate()
    if err:
        print err
        return None
    try:
        for line in out.split():
            if 'width=' in line:
                width = line.split('=')[1]
            if 'height=' in line:
                height = line.split('=')[1]
    except:
        return None
    # return width + 'x' + height
    return [int(width), int(height)]

#----------------------------------------------------------------------
def get_url_size(url):
    """str->int
    Get remote URL size by reading Content-Length.
    In bytes."""
    site = urllib.urlopen(url)
    meta = site.info()
    return int(meta.getheaders("Content-Length")[0])

#----------------------------------------------------------------------
def getvideosize(url, verbose=False):
    try:
        if url.startswith('http:') or url.startswith('https:'):
            ffprobe_command = ['ffprobe', '-icy', '0', '-loglevel', 'repeat+warning' if verbose else 'repeat+error', '-print_format', 'json', '-select_streams', 'v', '-show_format', '-show_streams', '-timeout', '60000000', '-user-agent', BILIGRAB_UA, url]
        else:
            ffprobe_command = ['ffprobe', '-loglevel', 'repeat+warning' if verbose else 'repeat+error', '-print_format', 'json', '-select_streams', 'v', '-show_streams', url]
        logcommand(ffprobe_command)
        ffprobe_process = subprocess.Popen(ffprobe_command, stdout=subprocess.PIPE)
        try:
            ffprobe_output = json.loads(ffprobe_process.communicate()[0].decode('utf-8', 'replace'))
        except KeyboardInterrupt:
            logging.warning('Cancelling getting video size, press Ctrl-C again to terminate.')
            ffprobe_process.terminate()
            return 0, 0
        width, height, widthxheight, duration, total_bitrate = 0, 0, 0, 0, 0
        try:
            if dict.get(ffprobe_output, 'format')['duration'] > duration:
                duration = dict.get(ffprobe_output, 'format')['duration']
        except:
            pass
        for stream in dict.get(ffprobe_output, 'streams', []):
            try:
                if duration == 0 and (dict.get(stream, 'duration') > duration):
                        duration = dict.get(stream, 'duration')
                if dict.get(stream, 'width')*dict.get(stream, 'height') > widthxheight:
                    width, height = dict.get(stream, 'width'), dict.get(stream, 'height')
                if dict.get(stream, 'bit_rate') > total_bitrate:
                    total_bitrate += int(dict.get(stream, 'bit_rate'))
            except Exception:
                pass
        if duration == 0:
            duration = int(get_url_size(url) * 8 / total_bitrate)
        return [[int(width), int(height)], int(float(duration))+1]
    except Exception as e:
        logorraise(e)
        return [[0, 0], 0]

#----------------------------------------------------------------------
def convert_ass_py3(filename, probe_software, resolution = [0, 0]):
    """str,str->None
    With danmaku2ass, branch master.
    https://github.com/m13253/danmaku2ass/
    Author: @m13253
    GPLv3
    A simple way to do that.
    resolution_str:1920x1080"""
    xml_name = os.path.abspath(filename + '.xml')
    ass_name = filename + '.ass'
    print('INFO: Converting danmaku to ASS file with danmaku2ass(main)...')
    print(resolution)
    print('INFO: Resolution is %dx%d' % (resolution[0], resolution[1]))
    if resolution == [0, 0]:
        print('INFO: Trying to get resolution...')
        resolution = get_resolution(filename, probe_software)
    print('INFO: Resolution is %dx%d' % (resolution[0], resolution[1]))
    if os.system('python3 %s/danmaku2ass3.py -o %s -s %dx%d -fs %d -a 0.8 -l 8 %s' % (LOCATION_DIR, ass_name, resolution[0], resolution[1], int(math.ceil(resolution[1] / 21.6)), xml_name)) == 0:
        print('INFO: The ASS file should be ready!')
    else:
        print('ERROR: Danmaku2ASS failed.')
        print('       Head to https://github.com/m13253/danmaku2ass/issues to complain about this.')

#----------------------------------------------------------------------
def convert_ass_py2(filename, probe_software, resolution = [0, 0]):
    """str,str->None
    With danmaku2ass, branch py2.
    https://github.com/m13253/danmaku2ass/tree/py2
    Author: @m13253
    GPLv3"""
    print('INFO: Converting danmaku to ASS file with danmaku2ass(py2)...')
    xml_name = filename + '.xml'
    if resolution == [0, 0]:
        print('INFO: Trying to get resolution...')
        resolution = get_resolution(filename, probe_software)
    print('INFO: Resolution is {width}x{height}'.format(width = resolution[0], height = resolution[1]))
    #convert_ass(xml_name, filename + '.ass', resolution)
    try:
        Danmaku2ASS(xml_name, filename + '.ass', resolution[0], resolution[1],
                    font_size = int(math.ceil(resolution[1] / 21.6)), text_opacity=0.8, comment_duration=8.0)
        print('INFO: The ASS file should be ready!')
    except Exception as e:
        print('ERROR: Danmaku2ASS failed: %s' % e)
        print('       Head to https://github.com/m13253/danmaku2ass/issues to complain about this.')
        if LOG_LEVEL == 1:
            traceback.print_exc()
        pass  #Or it may stop leaving lots of lines unprocessed

#----------------------------------------------------------------------
def download_danmaku(cid, filename):
    """str,str,int->None
    Download XML file, and convert to ASS(if required)
    Used to be in main(), but replaced due to the merge of -m (BiligrabLite).
    If danmaku only, will see whether need to export ASS."""
    print('INFO: Fetching XML...')
    os.system('curl -o "{filename}.xml" --compressed  http://comment.bilibili.com/{cid}.xml'.format(filename = filename, cid = cid))
    #os.system('gzip -d '+cid+'.xml.gz')
    print('INFO: The XML file, {filename}.xml should be ready...enjoy!'.format(filename = filename))

#----------------------------------------------------------------------
def logcommand(command_line):
    logging.debug('Executing: '+' '.join('\''+i+'\'' if ' ' in i or '&' in i or '"' in i else i for i in command_line))

#----------------------------------------------------------------------
def logorraise(message, debug=False):
    if debug:
        raise message
    else:
        logging.error(str(message))

########################################################################
class DanmakuOnlyException(Exception):

    '''Deal with DanmakuOnly to stop the main() function.'''
    #----------------------------------------------------------------------

    def __init__(self, value):
        self.value = value
    #----------------------------------------------------------------------

    def __str__(self):
        return repr(self.value)

########################################################################
class Danmaku2Ass2Exception(Exception):

    '''Deal with Danmaku2ASS2 to stop the main() function.'''
    #----------------------------------------------------------------------

    def __init__(self, value):
        self.value = value
    #----------------------------------------------------------------------

    def __str__(self):
        return repr(self.value)

########################################################################
class NoCidException(Exception):

    '''Deal with no cid to stop the main() function.'''
    #----------------------------------------------------------------------

    def __init__(self, value):
        self.value = value
    #----------------------------------------------------------------------

    def __str__(self):
        return repr(self.value)

########################################################################
class NoVideoURLException(Exception):

    '''Deal with no video URL to stop the main() function.'''
    #----------------------------------------------------------------------

    def __init__(self, value):
        self.value = value
    #----------------------------------------------------------------------

    def __str__(self):
        return repr(self.value)

########################################################################
class ExportM3UException(Exception):

    '''Deal with export to m3u to stop the main() function.'''
    #----------------------------------------------------------------------

    def __init__(self, value):
        self.value = value
    #----------------------------------------------------------------------

    def __str__(self):
        return repr(self.value)

#----------------------------------------------------------------------
def main(vid, p, oversea, cookies, download_software, concat_software, is_export, probe_software, danmaku_only):
    global cid, partname, title, videourl, is_first_run
    videourl = 'http://www.bilibili.com/video/av{vid}/index_{p}.html'.format(vid = vid, p = p)
    # Check both software
    print(concat_software, download_software)
    # Start to find cid, api
    cid, partname, title, pages = find_cid_api(vid, p, cookies)
    if cid is 0:
        print('WARNING: Cannot find cid, trying to do it brutely...')
        find_cid_flvcd(videourl)
    if cid is 0:
        if IS_SLIENT == 0:
            is_black3 = str(
                raw_input('WARNING: Strange, still cannot find cid... \nType y for trying the unpredictable way, or input the cid by yourself; Press ENTER to quit.'))
        else:
            is_black3 = 'y'
        if 'y' in str(is_black3):
            vid = str(int(vid) - 1)
            p = 1
            find_cid_api(int(vid) - 1, p)
            cid = cid + 1
        elif str(is_black3) is '':
            raise NoCidException('FATAL: Cannot get cid anyway!')
        else:
            cid = str(is_black3)
    # start to make folders...
    if title is not '':
        folder = title
    else:
        folder = cid
    if len(partname) is not 0:
        filename = partname
    elif title is not '':
        filename = title
    else:
        filename = cid
    # In case make too much folders
    folder_to_make = os.getcwd() + '/' + folder
    if is_first_run == 0:
        if not os.path.exists(folder_to_make):
            os.makedirs(folder_to_make)
        is_first_run = 1
        os.chdir(folder_to_make)
    # Download Danmaku
    download_danmaku(cid, filename)
    if is_export >= 1 and IS_M3U != 1 and danmaku_only == 1:
        rawurl = get_video(oversea, convert_m3u=True)
        check_dependencies_remote_resolution('ffprobe')
        resolution = getvideosize(rawurl[0])[0]
        convert_ass(filename, probe_software, resolution = resolution)
    if IS_M3U == 1:
        rawurl = []
        #M3U export, then stop
        if oversea in {'0', '1'}:
            rawurl = get_video(oversea, convert_m3u=True)
        else:
            duration_list = []
            rawurl = get_video(oversea, convert_m3u=False)
            for url in rawurl:
                duration_list.append(getvideosize(url)[1])
            rawurl = map(lambda x,y: (x, y), rawurl, duration_list)
        print(rawurl)
        resolution = getvideosize(rawurl[0][0])[0]
        m3u_file = make_m3u8(rawurl)
        f = open(filename + '.m3u', 'w')
        cwd = os.getcwd()
        m3u_file = m3u_file.encode("utf8")
        f.write(m3u_file)
        f.close()
        convert_ass(filename, probe_software, resolution = resolution)
        if LOG_LEVEL == 1:
            print_error(m3u_file)
        raise ExportM3UException('INFO: Export to M3U')
    if danmaku_only == 1:
        raise DanmakuOnlyException('INFO: Danmaku only')
    # Find video location
    print('INFO: Finding video location...')
    # try api
        # flvcd
    rawurl = get_video(oversea)
    if len(rawurl) == 0 and oversea != '4':  # hope this never happen
        print('WARNING: API failed, using falloff plan...')
        rawurl = find_link_flvcd(videourl)
    vid_num = len(rawurl)
    if IS_SLIENT == 0 and vid_num == 0:
        rawurl = list(str(raw_input('ERROR: Cannot get download URL! If you know the url, please enter it now: URL1|URL2...'))).split('|')
    vid_num = len(rawurl)
    if vid_num is 0:  # shit really hit the fan
        raise NoVIdeoURLException('FATAL: Cannot get video URL anyway!')
    print('INFO: {vid_num} videos in part {part_now} to download, fetch yourself a cup of coffee...'.format(vid_num = vid_num, part_now = part_now))
    for i in range(vid_num):
        video_link = rawurl[i]
        part_number = str(i)
        print('INFO: Downloading {slice_now} of {vid_num} videos in part {part_now}...'.format(slice_now = str(i + 1), vid_num = vid_num, part_now = part_now))
        # Call a function to support multiple download softwares
        download_video(part_number, download_software, video_link)
    concat_videos(concat_software, vid_num, filename)
    if is_export >= 1:
        try:
            convert_ass(filename, probe_software)
        except:
            print('WARNING: Problem with ASS convertion!')
            pass
    print('INFO: Part Done!')

#----------------------------------------------------------------------
def get_full_p(p_raw):
    """str->list"""
    p_list = []
    p_raw = p_raw.split(',')
    for item in p_raw:
        if '~' in item:
            # print(item)
            lower = 0
            higher = 0
            item = item.split('~')
            part_now = '0'
            try:
                lower = int(item[0])
            except:
                print('WARNING: Cannot read lower!')
            try:
                higher = int(item[1])
            except:
                print('WARNING: Cannot read higher!')
            if lower == 0 or higher == 0:
                if lower == 0 and higher != 0:
                    lower = higher
                elif lower != 0 and higher == 0:
                    higher = lower
                else:
                    print('WARNING: Cannot find any higher or lower, ignoring...')
                    # break
            mid = 0
            if higher < lower:
                mid = higher
                higher = lower
                lower = mid
            p_list.append(lower)
            while lower < higher:
                lower = lower + 1
                p_list.append(lower)
            # break
        else:
            try:
                p_list.append(int(item))
            except:
                print('WARNING: Cannot read "{item}", abondon it.'.format(item = item))
                # break
    p_list = list_del_repeat(p_list)
    return p_list

#----------------------------------------------------------------------
def check_dependencies_remote_resolution(software):
    """"""
    if 'ffprobe' in software:
        output = commands.getstatusoutput('ffprobe --help')
        if str(output[0]) == '32512':
            FFPROBE_USABLE = 0
        else:
            FFPROBE_USABLE = 1

#----------------------------------------------------------------------
def check_dependencies_exportm3u(IS_M3U):
    """int,str->int,str"""
    if IS_M3U == 1:
        output = commands.getstatusoutput('ffprobe --help')
        if str(output[0]) == '32512':
            err_input = str(raw_input('ERROR: ffprobe DNE, python3 does not exist or not callable! Do you want to exit, ignore or stop the converting?(e/i/s)'))
            if err_input == 'e':
                exit()
            elif err_input == '2':
                FFPROBE_USABLE = 0
            elif err_input == 's':
                IS_M3U = 0
            else:
                print('WARNING: Cannot read input, stop the converting!')
                IS_M3U = 0
        else:
            FFPROBE_USABLE = 1
    return IS_M3U

#----------------------------------------------------------------------
def check_dependencies_danmaku2ass(is_export):
    """int,str->int,str"""
    if is_export == 3:
        convert_ass = convert_ass_py3
        output = commands.getstatusoutput('python3 --help')
        if str(output[0]) == '32512' or not os.path.exists('danmaku2ass3.py'):
            err_input = str(
                raw_input(
                    'ERROR: danmaku2ass3.py DNE, python3 does not exist or not callable! Do you want to exit, use Python 2.x or stop the converting?(e/2/s)'))
            if err_input == 'e':
                exit()
            elif err_input == '2':
                convert_ass = convert_ass_py2
                is_export = 2
            elif err_input == 's':
                is_export = 0
            else:
                print('WARNING: Cannot read input, stop the converting!')
                is_export = 0
    elif is_export == 2 or is_export == 1:
        convert_ass = convert_ass_py2
        if not os.path.exists('danmaku2ass2.py'):
            err_input = str(
                raw_input(
                    'ERROR: danmaku2ass2.py DNE! Do you want to exit, use Python 3.x or stop the converting?(e/3/s)'))
            if err_input == 'e':
                exit()
            elif err_input == '3':
                convert_ass = convert_ass_py3
                is_export = 3
            elif err_input == 's':
                is_export = 0
            else:
                print('WARNING: Cannot read input, stop the converting!')
                is_export = 0
    else:
        convert_ass = convert_ass_py2
    return is_export, convert_ass

#----------------------------------------------------------------------
def usage():
    """"""
    print('''
    Biligrab
    
    https://github.com/cnbeining/Biligrab
    http://www.cnbeining.com/
    
    Beining@ACICFG
    
    
    
    Usage:
    
    python biligrab.py (-h) (-a) (-p) (-s) (-c) (-d) (-v) (-l) (-e) (-p) (-m) (-n) (-u) (-t)
    
    -h: Default: None
        Print this usage file.
        
    -a: Default: None
        The av number.
        If not set, Biligrab will use the falloff interact mode.
        Support "~", "," and mix use.
        Examples:
            Input        Output
              1           [1]
             1,2         [1, 2]
             1~3        [1, 2, 3]
            1,2~3       [1, 2, 3]
            
    -p: Default: 0
        The part number.
        Able to use the same syntax as "-a".
        If set to 0, Biligrab will download all the avalable parts in the video.
        
    -s: Default: 0
    Source to download.
    0: The original API source, can be Letv backup,
       and can failed if the original video is not avalable(e.g., deleted)
    1: The CDN API source, "oversea accelerate".
       Can be MINICDN backup in Mainland China or oversea.
       Good to bypass some bangumi's limit.
    2: Force to use the original source.
       Use Flvcd to parase the video, but would fail if
       1) The original source DNE, e.g., some old videos
       2) The original source is Letvcloud itself.
       3) Other unknown reason(s) that stops Flvcd from parasing the video.
    For any video that failed to parse, Biligrab will try to use Flvcd.
    (Mainly for oversea users regarding to copyright-restricted bangumies.)
    If the API is blocked, Biligrab would fake the UA.
    3: (Not stable) Use the HTML5 API.
       This works for downloading some cached Letvcloud videos, but is slow, and would fail for no reason sometimes.
    4: Use Flvcd.
       Good to fight with oversea and copyright restriction, but not working with iQiyi.
       
    -c: Default: ./bilicookies
    The path of cookies.
    Use cookies to visit member-only videos.
    
    -d: Default: None
    Set the desired download software.
    Biligrab supports aria2c(16 threads), axel(20 threads), wget and curl by far.
    If not set, Biligrab will detect an avalable one;
    If none of those is avalable, Biligrab will quit.
    For more software support, please open an issue at https://github.com/cnbeining/Biligrab/issues/
    
    -v: Default:None
    Set the desired concatenate software.
    Biligrab supports ffmpeg by far.
    If not set, Biligrab will detect an avalable one;
    If none of those is avalable, Biligrab will quit.
    For more software support, please open an issue at https://github.com/cnbeining/Biligrab/issues/
    Make sure you include a *working* command line example of this software!
    
    -l: Default: 0
    Dump the log of the output for better debugging.
    
    -e: Default: 1
    Export Danmaku to ASS file.
    Fulfilled with danmaku2ass(https://github.com/m13253/danmaku2ass/tree/py2),
    Author: @m13253, GPLv3 License.
    *For issue with this function, if you think the problem lies on the danmaku2ass side,
    please open the issue at both projects.*
    If set to 1 or 2, Biligrab will use Danmaku2ass's py2 branch.
    If set to 3, Biligrab will use Danmaku2ass's master branch, which would require
    a python3 callable via 'python3'.
    If python3 not callable or danmaku2ass2/3 DNE, Biligrab will ask for action.
    
    -p: Default: None
    Set the probe software.
    Biligrab supports Mediainfo and FFprobe.
    If not set, Biligrab will detect an avalable one;
    If none of those is avalable, Biligrab will quit.
    For more software support, please open an issue at https://github.com/cnbeining/Biligrab/issues/
    Make sure you include a *working* command line example of this software!
    
    -m: Default: 0
    Only download the danmaku.
    
    -n: Default: 0
    Slient Mode.
    Biligrab will not ask any question.
    
    -u: Default: 0
    Export video link to .m3u file, which can be used with MPlayer, mpc, VLC, etc.
    Biligrab will export a m3u8 instead of downloading any video(s).
    Can be broken with sources other than 0 or 1.
    
    -t: Default: None
    The number of Mylist.
    Biligrab will process all the videos in this list.
    ''')


#----------------------------------------------------------------------
if __name__ == '__main__':
    is_first_run, is_export, danmaku_only, IS_SLIENT, IS_M3U, mylist = 0, 1, 0, 0, 0, 0
    argv_list,av_list = [], []
    argv_list = sys.argv[1:]
    p_raw, vid, oversea, cookiepath, download_software, concat_software, probe_software, vid_raw = '', '', '', '', '', '', '', ''
    convert_ass = convert_ass_py2
    try:
        opts, args = getopt.getopt(argv_list, "ha:p:s:c:d:v:l:e:b:m:n:u:t:",
                                   ['help', "av", 'part', 'source', 'cookie', 'download', 'concat', 'log', 'export', 'probe', 'danmaku', 'slient', 'm3u', 'mylist'])
    except getopt.GetoptError:
        usage()
        exit()
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            exit()
        if o in ('-a', '--av'):
            vid_raw = a
            try:
                argv_list.remove('-a')
            except:
                break
        if o in ('-p', '--part'):
            p_raw = a
            try:
                argv_list.remove('-p')
            except:
                break
        if o in ('-s', '--source'):
            oversea = a
            try:
                argv_list.remove('-s')
            except:
                break
        if o in ('-c', '--cookie'):
            cookiepath = a
            try:
                argv_list.remove('-c')
            except:
                print('INFO: No cookie path set, use default: ./bilicookies')
                cookiepath = './bilicookies'
                break
        if o in ('-d', '--download'):
            download_software = a
            try:
                argv_list.remove('-d')
            except:
                break
        if o in ('-v', '--concat'):
            concat_software = a
            try:
                argv_list.remove('-v')
            except:
                break
        if o in ('-l', '--log'):
            LOG_LEVEL = int(a)
            print('INFO: Log enabled!')
            try:
                argv_list.remove('-l')
            except:
                LOG_LEVEL = 0
                break
        if o in ('-e', '--export'):
            is_export = int(a)
            try:
                argv_list.remove('-e')
            except:
                is_export = 1
                break
        if o in ('-b', '--probe'):
            probe_software = a
            try:
                argv_list.remove('-b')
            except:
                break
        if o in ('-m', '--danmaku'):
            danmaku_only = int(a)
            try:
                argv_list.remove('-m')
            except:
                break
        if o in ('-n', '--slient'):
            IS_SLIENT = int(a)
            try:
                argv_list.remove('-n')
            except:
                break
        if o in ('-u', '--m3u'):
            IS_M3U = int(a)
            try:
                argv_list.remove('-u')
            except:
                break
        if o in ('-t', '--mylist'):
            mylist = a
            try:
                argv_list.remove('-t')
            except:
                break
    if len(vid_raw) == 0:
        vid_raw = str(raw_input('av'))
        p_raw = str(raw_input('P'))
        oversea = str(raw_input('Source?'))
        cookiepath = './bilicookies'
    av_list = get_full_p(vid_raw)
    if mylist != 0:
        av_list += mylist_to_aid_list(mylist)
    if LOG_LEVEL == 1:
        print(av_list)
    if len(cookiepath) == 0:
        cookiepath = './bilicookies'
    if len(p_raw) == 0:
        print('INFO: No part number set, download all the parts.')
        p_raw = '0'
    if len(oversea) == 0:
        oversea = '0'
        print('INFO: Oversea not set, use original API(methon 0).')
    IS_M3U = check_dependencies_exportm3u(IS_M3U)
    if IS_M3U == 1 and oversea not in {'0', '1'}:
        # See issue #8
        print('INFO: M3U exporting with source other than 0 or 1 can be broken, and lead to wrong duration!')
        if IS_SLIENT == 0:
            input_raw = str(raw_input('Enter "q" to quit, or enter the source you want.'))
            if input_raw == 'q':
                exit()
            else:
                oversea = input_raw
    concat_software, download_software, probe_software = check_dependencies(download_software, concat_software, probe_software)
    p_list = get_full_p(p_raw)
    if len(av_list) > 1 and len(p_list) > 1:
        print('WARNING: You are downloading multi parts from multiple videos! This may result in unpredictable outputs!')
        if IS_SLIENT == 0:
            input_raw = str(
                raw_input('Enter "y" to continue, "n" to only download the first part, "q" to quit, or enter the part number you want.'))
            if input_raw == 'y':
                pass
            elif input_raw == 'n':
                p_list = ['1']
            elif input_raw == 'q':
                exit()
            else:
                p_list = get_full_p(input_raw)
    cookies = read_cookie(cookiepath)
    global BILIGRAB_HEADER, BILIGRAB_UA
    # deal with danmaku2ass's drama / Twice in case someone failed to check dependencies
    is_export, convert_ass = check_dependencies_danmaku2ass(is_export)
    is_export, convert_ass = check_dependencies_danmaku2ass(is_export)
    BILIGRAB_UA = 'Biligrab / ' + str(VER) + ' (cnbeining@gmail.com)'
    BILIGRAB_HEADER = {'User-Agent': BILIGRAB_UA, 'Cache-Control': 'no-cache', 'Pragma': 'no-cache', 'Cookie': cookies[0]}
    if LOG_LEVEL == 1:
        print('!!!!!!!!!!!!!!!!!!!!!!!\nWARNING: This log contains some sensive data. You may want to delete some part of the data before you post it publicly!\n!!!!!!!!!!!!!!!!!!!!!!!')
        print(BILIGRAB_HEADER)
        try:
            request = urllib2.Request('http://ipinfo.io/json', headers=FAKE_HEADER)
            response = urllib2.urlopen(request)
            data = response.read()
            print('INFO: Dumping info...')
            print('!!!!!!!!!!!!!!!!!!!!!!!\nWARNING: This log contains some sensive data. You may want to delete some part of the data before you post it publicly!\n!!!!!!!!!!!!!!!!!!!!!!!')
            print('=======================DUMP DATA==================')
            print(data)
            print('========================DATA END==================')
            print('DEBUG: ' + str(av_list))
        except:
            print('WARNING: Cannot connect to IP-geo database server!')
            pass
    for av in av_list:
        vid = str(av)
        if str(p_raw) == '0':
            print('INFO: You are downloading all the parts in this video...')
            try:
                p_raw = str('1~' + find_cid_api(vid, p_raw, cookies)[3])
                p_list = get_full_p(p_raw)
            except:
                print('WARNING: Error when reading all the parts!')
                if IS_SLIENT == 0:
                    input_raw = str(
                        raw_input('Enter the part number you want, or "q" to quit.'))
                    if input_raw == '0':
                        print('ERROR: Cannot use all the parts!')
                        exit()
                    elif input_raw == 'q':
                        exit()
                    else:
                        p_list = get_full_p(input_raw)
                else:
                    print('WARNING: Download the first part of the video...')
                    p_raw = '1'
                    p_list = [1]
            print('INFO: Your target download is av{vid}, part {p_raw}, from source {oversea}'.format(vid = vid, p_raw = p_raw, oversea = oversea))
        for p in p_list:
            reload(sys)
            sys.setdefaultencoding('utf-8')
            part_now = str(p)
            try:
                print('INFO: Downloading part ' + str(p) + ' ...')
                main(vid, p, oversea,cookies, download_software, concat_software, is_export, probe_software, danmaku_only)
            except DanmakuOnlyException:
                pass
            except ExportM3UException:
                pass
            except Exception as e:
                print('ERROR: Biligrab failed: %s' % e)
                print('       If you think this should not happen, please dump your log using "-l", and open a issue ar https://github.com/cnbeining/Biligrab/issues .')
                print('       Make sure you delete all the sensive data before you post it publicly.')
                if LOG_LEVEL == 1:
                    traceback.print_exc()
    exit()

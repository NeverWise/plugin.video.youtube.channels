#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import HTMLParser
import json
import os
import pickle
import re
import socket
import sys
import urllib
import urllib2
import urlparse

import xbmcaddon
import xbmcgui
import xbmcplugin


class Channel(object):
	def __init__(self, name, user, thumb, category):
		self.name = name
		self.user = user
		self.thumb = fix_thumbnail(thumb)
		self.category = category

	def __repr__(self):
		return '{0}({1}, {2}, {3}, {4}, {5})'.format(self.__class__.__name__, repr(self.name), repr(self.user), repr(self.thumb), repr(self.category), repr(self.mode))

	def replace(self, **attrs):
		for attr, value in attrs.items():
			setattr(self, attr, value)
		return self


def translation(id):
	return addon.getLocalizedString(id)


def read_channels():
	try:
		try:
			with open(channelFile, 'rb') as f:
				for channel in pickle.load(f):
					if isinstance(channel, Channel):
						yield channel
					else:
						yield Channel(*channel)
		except:
			with open(channelFile) as channels:
				for line in channels:
					match = re.match('^(?P<name>.+?)#(?P<user>.+?)#(?P<thumb>.+?)#(?P<category>.+?)#$', line.strip())
					if match:
						yield Channel(match.group('name'), match.group('user'), match.group('thumb') or 'DefaultFolder.png', match.group('category'))
	except IOError:
		pass


def write_channels(channels):
	with open(channelFile, 'wb') as f:
		pickle.dump(channels, f)


def get_categories():
	return [category for category in (addon.getSetting('cat_' + str(i)) for i in range(20)) if category != '']


def build_url(**query):
	urlParams = {}
	for key, value in query.items():
		if hasattr(value, 'encode'):
			value = value.encode('utf-8')
		urlParams[key] = value
	return '{0}?{1}'.format(sys.argv[0], urllib.urlencode(urlParams))


def build_context_entry(textid, **query):
	return translation(textid), 'RunPlugin(' + build_url(**query) + ')'


def extract_videos(content):
	entries = content.split('<li class="channels-content-item yt-shelf-grid-item">')[1:]
	for entry in entries:
		try:
			yid = re.search('<a href="/watch\?v=(?P<id>[^"]+)"', entry).group('id')
			time = re.search('<span class="video-time".*>([0-9:]+)</span>', entry)
			time = time.group(1).split(':')
			if len(time) == 2:
				duration = int(time[0]) * 60 + int(time[1])
			else:
				duration = int(time[0]) * 3600 + int(time[1]) * 60 + int(time[2])
			title = HTMLParser.HTMLParser().unescape(re.search('<h3 class="yt-lockup-title.*">.*>(?P<title>[^<]+)</a>', entry).group('title'))
			yield yid, duration, title
		except AttributeError:
			continue


def fix_thumbnail(thumb):
	if thumb.startswith('//'):
		thumb = 'https:' + thumb
	return re.sub('/s[0-9]+([^/]+)/', '/s' + addon.getSetting('thumbnailResolution') + '\g<1>/', thumb)


def getYoutubeUrl(youtubeID):
	return ('plugin://video/YouTube/?path=/root/video&action=play_video&videoid=' if xbox else 'plugin://plugin.video.youtube/play/?video_id=') + youtubeID


def getUrl(route, **query):
	url = 'https://www.youtube.com{0}'
	if route[0:1] == '/':
		url = url.format(route)
	else:
		url = url.join('/', route);
	req = urllib2.Request(url + ('?' + urllib.urlencode(query) if query else ''))
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:19.0) Gecko/20100101 Firefox/19.0')
	response = urllib2.urlopen(req)
	charset = dict(x.split('=') for x in response.info().getplist() if '=' in x).get('charset', None)
	result = response.read()
	response.close()
	if charset:
		result = result.decode(charset)
	return result


def addItem(name, iconImage='DefaultFolder.png', thumbnailImage=None, contextMenu=[], isFolder=True, **args):
	item = xbmcgui.ListItem(name)
	if iconImage:
		item.setIconImage(iconImage)
	if thumbnailImage:
		item.setThumbnailImage(thumbnailImage)
	if contextMenu:
		item.addContextMenuItems(contextMenu)
	item.setInfo(type='Video', infoLabels={'Title': name})
	xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(**args), listitem=item, isFolder=isFolder)


def myChannels():
	categories = set()
	empty = True
	for channel in read_channels():
		if channel.category == 'NoCat':
			addItem(
				channel.name,
				thumbnailImage=channel.thumb,
				contextMenu=[
					build_context_entry(30026, target='playChannel', user=channel.user),
					build_context_entry(30024, target='addChannel', user=channel.user, name=channel.name, thumb=channel.thumb),
					build_context_entry(30030, target='addChannel', user=channel.user, name=channel.name, thumb=channel.thumb, category=channel.category, moving=True),
					build_context_entry(30028, target='updateThumb'),
					build_context_entry(30003, target='removeChannel', user=channel.user),
					build_context_entry(30006, target='search', category=channel.category),
				],
				target='listVideos',
				user=channel.user
			)
		elif channel.category not in categories:
			categories.add(channel.category)
			addItem(
				'- ' + channel.category,
				contextMenu=[
					build_context_entry(30009, target='removeCat', category=channel.category),
					build_context_entry(30012, target='renameCat', category=channel.category),
					build_context_entry(30006, target='search', category=channel.category),
				],
				target='listCat',
				category=channel.category,
			)
		empty = False
	if empty:
		search(None)
	else:
		xbmcplugin.endOfDirectory(pluginhandle)
		xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
		if forceViewMode == 'true':
			xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def listCat(category):
	xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
	for channel in read_channels():
		if channel.category == category:
			addItem(
				channel.name,
				thumbnailImage=channel.thumb,
				contextMenu=[
					build_context_entry(30026, target='playChannel', user=channel.user),
					build_context_entry(30024, target='addChannel', user=channel.user, name=channel.name, thumb=channel.thumb),
					build_context_entry(30030, target='addChannel', user=channel.user, name=channel.name, thumb=channel.thumb, category=channel.category, moving=True),
					build_context_entry(30028, target='updateThumb'),
					build_context_entry(30003, target='removeChannel', user=channel.user),
					build_context_entry(30006, target='search', category=channel.category),
				],
				target='listVideos',
				user=channel.user,
				mode=channel.mode,
			)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == 'true':
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def search(category):
	keyboard = xbmc.Keyboard('', translation(30006))
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		search_string = keyboard.getText()
		xbmc.executebuiltin('ActivateWindow(videolibrary, ' + build_url(target='listSearchChannels', query=search_string, category=category) + ')')


def listSearchChannels(query, category, page='1'):
	content = getUrl('/results', filters='channel', search_query=query, page=page)
	entries = content.split('<li><div')[1:]
	for entry in entries:
		try:
			user_name = re.search('<a.+href="(.+?)".+<h3.+?title="(.+?)"', entry)
			name = HTMLParser.HTMLParser().unescape(user_name.group(2))
			user = user_name.group(1)
			try:
				thumb = re.search('data-thumb="(?P<thumb>[^"]+)"', entry).group('thumb')
			except AttributeError:
				thumb = re.search('<img src="(?P<thumb>[^"]+)"', entry).group('thumb')
			thumb = fix_thumbnail(thumb)
			title = None
			if entry.find('yt-subscriber-count') > -1:
				title = '[B]{0}[/B] - {1} {2}'.format(name, re.search('>(?P<subscribers>[0-9.]+)</span>', entry).group('subscribers'), translation(30034))
			else:
				title = '[B]{0}[/B]'.format(name)
			addItem(
				title,
				thumbnailImage=thumb,
				contextMenu=[
					build_context_entry(30026, target='playChannel', user=user),
					build_context_entry(30002, target='addChannel', user=user, name=name, thumb=thumb, category=category),
				],
				target='listVideos',
				user=user,
			)
		except AttributeError:
			continue
	match = re.search('data-link-type="next" data-page="(?P<page>[0-9]+)"', content)
	if match:
		addItem(translation(30007), target='listSearchChannels', query=query, category=category, page=match.group('page'))
	xbmcplugin.endOfDirectory(pluginhandle)


def listVideos(user, mode=0, continuation=None):
	if continuation is not None:
		jsondata = json.loads(getUrl(continuation))
		content = jsondata.get('content_html') + jsondata.get('load_more_widget_html')
	else:
		content = getUrl('{0}/videos'.format(user), view=mode)
	try:
		continuation = re.search('data-uix-load-more-href="(?P<url>[^"]+)"', content).group('url').replace('&amp;', '&')
	except AttributeError:
		continuation = None
	for yid, duration, title in extract_videos(content):
		item = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage='http://img.youtube.com/vi/' + yid + '/0.jpg')
		item.setInfo(type='Video', infoLabels={'Title': title})
		item.addStreamInfo('video', {'duration': duration})
		item.setProperty('IsPlayable', 'true')
		xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(target='playVideo', url=yid), listitem=item)
	if continuation:
		addItem(translation(30007), target='listVideos', user=user, mode=mode, continuation=continuation)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == 'true':
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def playVideo(url):
	listitem = xbmcgui.ListItem(path=getYoutubeUrl(url))
	return xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)


def playChannel(user, mode=0):
	content = getUrl('{0}/videos'.format(user), view=mode)
	playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	playlist.clear()
	for yid, duration, title in extract_videos(content):
		listitem = xbmcgui.ListItem(title)
		playlist.add(getYoutubeUrl(yid), listitem)
	xbmc.Player().play(playlist)


def addChannel(name, user, thumb, category=None, mode=0, moving=False):
	categories = [translation(30027)] + get_categories() + ['- ' + translation(30005)]
	while category not in categories + ['NoCat']:
		dialog = xbmcgui.Dialog()
		index = dialog.select(translation(30004), categories)
		if index < 0:
			return
		elif index == len(categories) - 1:
			addon.openSettings()
		elif index == 0:
			category = 'NoCat'
		else:
			category = categories[index]

	newChannels = []
	for channel in read_channels():
		if channel.user != user:
			newChannels.append(channel)

	newChannels.append(Channel(name, user, thumb, category))
	write_channels(newChannels)

	if not moving:
		try:
			xbmc.executebuiltin('XBMC.Notification({0},{1},5000,{2})'.format(translation(30018), name, notificationIcon))
		except:
			pass
	xbmc.executebuiltin('Container.Refresh')


def removeChannel(user):
	newChannels = []
	channelToBeRemoved = None
	for channel in read_channels():
		if channel.user != user:
			newChannels.append(channel)
		else:
			channelToBeRemoved = channel
	write_channels(newChannels)

	if channelToBeRemoved:
		try:
			xbmc.executebuiltin('XBMC.Notification({0},{1},5000),{2})'.format(translation(30019), channelToBeRemoved.name, notificationIcon))
		except:
			pass
	xbmc.executebuiltin('Container.Refresh')


def updateThumb():
	xbmc.executebuiltin('XBMC.Notification({0},{1},5000,{2})'.format(translation(30031), translation(30032), notificationIcon))
	newChannels = []
	for channel in read_channels():
		content = getUrl(channel.user)
		thumbnail = re.search('<link itemprop="thumbnailUrl" href="(?P<thumbnail>[^"]+)">', content)
		if thumbnail:
			newthumb = fix_thumbnail(thumbnail.group('thumbnail'))
			channel.replace(thumb=newthumb)
		newChannels.append(channel)
	write_channels(newChannels)
	xbmc.executebuiltin('Container.Refresh')
	xbmc.executebuiltin('XBMC.Notification({0},{1},5000,{2})'.format(translation(30031), translation(30033), notificationIcon))


def removeCat(category):
	if xbmcgui.Dialog().ok('Info:', translation(30010) + '?'):
		write_channels([channel for channel in read_channels() if channel.category != category])
		xbmc.executebuiltin('Container.Refresh')


def renameCat(category):
	keyboard = xbmc.Keyboard(category, translation(30011) + ' ' + category)
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		newName = keyboard.getText()
		write_channels([channel.replace(category=newName) if channel.category == category else channel for channel in read_channels()])
		xbmc.executebuiltin('Container.Refresh')


socket.setdefaulttimeout(30)
pluginhandle = int(sys.argv[1])
addonID = 'plugin.video.youtube.channels'
xbox = xbmc.getCondVisibility('System.Platform.xbox')
addon = xbmcaddon.Addon(addonID)
addon_work_folder = xbmc.translatePath('special://profile/addon_data/' + addonID)
channelFile = xbmc.translatePath('special://profile/addon_data/' + addonID + '/youtube.channels')
forceViewMode = addon.getSetting('forceView')
viewMode = str(addon.getSetting('viewMode'))
notificationIcon = os.path.join(addon.getAddonInfo('path'), 'icon.png')

if not os.path.isdir(addon_work_folder):
	os.mkdir(addon_work_folder)


args = {}
for key, values in urlparse.parse_qs(sys.argv[2][1:]).items():
	if len(values) == 1:
		values = values[0].decode('utf-8')
	args[key] = values

target = args.pop('target', 'myChannels')
locals()[target](**args)

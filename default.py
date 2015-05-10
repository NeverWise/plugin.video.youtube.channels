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


def translation(id):
	return addon.getLocalizedString(id)


def read_channels():
	try:
		try:
			with open(channelFile, 'rb') as f:
				for channel in pickle.load(f):
					yield channel[0], channel[1], fix_thumbnail(channel[2]), channel[3]
		except:
			with open(channelFile) as channels:
				for line in channels:
					match = re.match('^(?P<name>.+?)#(?P<user>.+?)#(?P<thumb>.+?)#(?P<category>.+?)#$', line.strip())
					if match:
						yield match.group('name'), match.group('user'), match.group('thumb') or "DefaultFolder.png", match.group('category')
	except IOError:
		pass


def write_channels(channels):
	with open(channelFile, 'wb') as f:
		pickle.dump(channels, f)


def get_categories():
	return [category for category in (addon.getSetting("cat_" + str(i)) for i in range(20)) if category != ""]


def build_url(**query):
	return sys.argv[0] + '?' + urllib.urlencode({key: (value.encode('utf-8') if hasattr(value, 'encode') else value) for key, value in query.items()})


def build_context_entry(textid, **query):
	return translation(textid), 'RunPlugin(' + build_url(**query) + ')'


def extract_videos(content):
	entries = content.split('<li class="channels-content-item yt-shelf-grid-item">')[1:]
	for entry in entries:
		try:
			yid = re.search('<a href="/watch\?v=(?P<id>[^"]+)"', entry).group('id')
			time = re.search('<span class="video-time".*>(?P<minutes>[0-9]+):(?P<seconds>[0-9]+)</span>', entry)
			duration = int(time.group('minutes')) * 60 + int(time.group('seconds'))
			title = HTMLParser.HTMLParser().unescape(re.search('<h3 class="yt-lockup-title">.*>(?P<title>[^<]+)</a>', entry).group('title'))
			yield yid, duration, title
		except AttributeError:
			continue


def fix_thumbnail(thumb):
	if thumb.startswith('//'):
		thumb = 'https:' + thumb
	return re.sub('/s[0-9]+([^/]+)/', '/s' + addon.getSetting('thumbnailResolution') + '\g<1>/', thumb)


def getYoutubeUrl(youtubeID):
	return ("plugin://video/YouTube/?path=/root/video&action=play_video&videoid=" if xbox else "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=") + youtubeID


def getUrl(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:19.0) Gecko/20100101 Firefox/19.0')
	response = urllib2.urlopen(req)
	link = response.read()
	response.close()
	return link


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
	for name, user, thumb, category in read_channels():
		if category == "NoCat":
			addItem(
				name,
				thumbnailImage=thumb,
				contextMenu=[
					build_context_entry(30026, target='playChannel', user=user),
					build_context_entry(30024, target='addChannel', user=user, name=name, thumb=thumb),
					build_context_entry(30028, target='updateThumb', user=user),
					build_context_entry(30003, target='removeChannel', user=user),
					build_context_entry(30006, target='search'),
				],
				target='listVideos',
				user=user,
			)
		elif category not in categories:
			categories.add(category)
			addItem(
				'- ' + category,
				contextMenu=[
					build_context_entry(30009, target='removeCat', category=category),
					build_context_entry(30012, target='renameCat', category=category),
					build_context_entry(30006, target='search'),
				],
				target='listCat',
				category=category,
			)
		empty = False
	if empty:
		search()
	else:
		xbmcplugin.endOfDirectory(pluginhandle)
		xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
		if forceViewMode == "true":
			xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def listCat(category):
	xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
	for name, user, thumb, cat in read_channels():
		if cat == category:
			addItem(
				name,
				thumbnailImage=thumb,
				contextMenu=[
					build_context_entry(30026, target='playChannel', user=user),
					build_context_entry(30024, target='addChannel', user=user, name=name, thumb=thumb),
					build_context_entry(30028, target='updateThumb', user=user),
					build_context_entry(30003, target='removeChannel', user=user),
				],
				target='listVideos',
				user=user,
			)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == "true":
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def search():
	keyboard = xbmc.Keyboard('', translation(30006))
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		search_string = keyboard.getText().replace(" ", "+")
		xbmc.executebuiltin('ActivateWindow(videolibrary, ' + build_url(target='listSearchChannels', query=search_string) + ')')


def listSearchChannels(query, page='1'):
	content = getUrl('https://www.youtube.com/results?filters=channel&search_query={}&page={}'.format(query, page)).decode('utf-8')
	entries = content.split('<li><div')[1:]
	for entry in entries:
		try:
			name = HTMLParser.HTMLParser().unescape(re.search('title="(?P<name>[^"]+)"', entry).group('name'))
			user = re.search('href="/user/(?P<user>[^"]+)"', entry).group('user')
			try:
				thumb = re.search('data-thumb="(?P<thumb>[^"]+)"', entry).group('thumb')
			except AttributeError:
				thumb = re.search('<img src="(?P<thumb>[^"]+)"', entry).group('thumb')
			thumb = fix_thumbnail(thumb)
			subscribers = re.search('>(?P<subscribers>[0-9.]+)</span>', entry).group('subscribers')
			addItem(
				'[B]{}[/B] - {} subscribers'.format(name, subscribers),
				thumbnailImage=thumb,
				contextMenu=[
					build_context_entry(30026, target='playChannel', user=user),
					build_context_entry(30002, target='addChannel', user=user, name=name, thumb=thumb),
				],
				target='listVideos',
				user=user,
			)
		except AttributeError:
			continue
	match = re.search('data-link-type="next" data-page="(?P<page>[0-9]+)"', content)
	if match:
		addItem(translation(30007), target='listSearchChannels', query=query, page=match.group('page'))
	xbmcplugin.endOfDirectory(pluginhandle)


def listVideos(user, continuation=None):
	if continuation is not None:
		jsondata = json.loads(getUrl('https://www.youtube.com' + continuation))
		content = jsondata.get('content_html') + jsondata.get('load_more_widget_html')
	else:
		content = getUrl('https://www.youtube.com/user/{}/videos?view=0'.format(user)).decode('utf-8')
	try:
		continuation = re.search('data-uix-load-more-href="(?P<url>[^"]+)"', content).group('url').replace('&amp;', '&')
	except AttributeError:
		continuation = None
	for yid, duration, title in extract_videos(content):
		item = xbmcgui.ListItem(title, iconImage="DefaultVideo.png", thumbnailImage="http://img.youtube.com/vi/" + yid + "/0.jpg")
		item.setInfo(type="Video", infoLabels={"Title": title})
		item.addStreamInfo('video', {'duration': duration})
		item.setProperty('IsPlayable', 'true')
		xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(target='playVideo', url=yid), listitem=item)
	if continuation:
		addItem(translation(30007), target='listVideos', user=user, continuation=continuation)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == "true":
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def playVideo(url):
	listitem = xbmcgui.ListItem(path=getYoutubeUrl(url))
	return xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)


def playChannel(user):
	content = getUrl('https://www.youtube.com/user/{}/videos?view=0'.format(user)).decode('utf-8')
	playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	playlist.clear()
	for yid, duration, title in extract_videos(content):
		listitem = xbmcgui.ListItem(title)
		playlist.add(getYoutubeUrl(yid), listitem)
	xbmc.Player().play(playlist)


def addChannel(name, user, thumb):
	while True:
		categories = [translation(30027)] + get_categories() + ["- " + translation(30005)]
		dialog = xbmcgui.Dialog()
		index = dialog.select(translation(30004), categories)
		if index >= 0:
			category = categories[index]
			if category == categories[-1]:
				addon.openSettings()
				continue
			elif category != "":
				if category == translation(30027):
					category = "NoCat"
				channels = set(channel for channel in read_channels() if channel[1] != user)
				channels.add((name, user, thumb, category))
				write_channels(channels)
				if showMessages == "true":
					xbmc.executebuiltin('XBMC.Notification(Info:,' + translation(30018).format(channel=name) + ',5000)')
				xbmc.executebuiltin("Container.Refresh")
		break


def removeChannel(user):
	write_channels([channel for channel in read_channels() if channel[1] != user])
	if showMessages == "true":
		xbmc.executebuiltin('XBMC.Notification(Info:,' + translation(30019).format(channel=user) + ',5000)')
	xbmc.executebuiltin("Container.Refresh")


def updateThumb(user):
	content = getUrl('https://www.youtube.com/user/{}'.format(user)).decode('utf-8')
	thumbnail = re.search('<link itemprop="thumbnailUrl" href="(?P<thumbnail>[^"]+)">', content)
	if thumbnail:
		newthumb = fix_thumbnail(thumbnail.group('thumbnail'))
		write_channels([(oname, ouser, newthumb if ouser == user else othumb, ocategory) for oname, ouser, othumb, ocategory in read_channels()])
		xbmc.executebuiltin("Container.Refresh")


def removeCat(category):
	if xbmcgui.Dialog().ok('Info:', translation(30010) + "?"):
		write_channels([channel for channel in read_channels() if channel[3] != category])
		xbmc.executebuiltin("Container.Refresh")


def renameCat(category):
	keyboard = xbmc.Keyboard(category, translation(30011) + " " + category)
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		newName = keyboard.getText()
		write_channels([(oname, ouser, othumb, newName if ocategory == category else ocategory) for oname, ouser, othumb, ocategory in read_channels()])
		xbmc.executebuiltin("Container.Refresh")


socket.setdefaulttimeout(30)
pluginhandle = int(sys.argv[1])
addonID = 'plugin.video.youtube.channels'
xbox = xbmc.getCondVisibility("System.Platform.xbox")
addon = xbmcaddon.Addon(addonID)
addon_work_folder = xbmc.translatePath("special://profile/addon_data/" + addonID)
channelFile = xbmc.translatePath("special://profile/addon_data/" + addonID + "/youtube.channels")
forceViewMode = addon.getSetting("forceView")
viewMode = str(addon.getSetting("viewMode"))
showMessages = str(addon.getSetting("showMessages"))

if not os.path.isdir(addon_work_folder):
	os.mkdir(addon_work_folder)


args = {key: (values[0].decode('utf-8') if len(values) == 1 else values) for key, values in urlparse.parse_qs(sys.argv[2][1:]).items()}
target = args.pop('target', 'myChannels')
locals()[target](**args)

#!/usr/bin/python
# -*- coding: utf-8 -*-
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
	return addon.getLocalizedString(id).encode('utf-8')


def read_channels():
	try:
		try:
			with open(channelFile, 'rb') as f:
				for channel in pickle.load(f):
					yield channel
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
	return sys.argv[0] + '?' + urllib.urlencode(query)


def build_context_entry(textid, **query):
	return translation(textid), 'RunPlugin(' + build_url(**query) + ')'


def getYoutubeUrl(youtubeID):
	return ("plugin://video/YouTube/?path=/root/video&action=play_video&videoid=" if xbox else "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=") + youtubeID


def updateThumb(edit_user):
	def newthumb():
		content = getUrl("http://www.youtube.com/user/" + edit_user)
		match = re.search('\'CHANNEL_ID\', "UC(.+?)"', content)
		return "http://img.youtube.com/i/" + match.group(0) + "/mq1.jpg"
	write_channels([(name, user, newthumb() if user == edit_user and thumb == "DefaultFolder.png" else thumb, category) for name, user, thumb, category in read_channels()])


def getUrl(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:19.0) Gecko/20100101 Firefox/19.0')
	response = urllib2.urlopen(req)
	link = response.read()
	response.close()
	return link


def cleanTitle(title):
	title = title.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&#039;", "\\").replace("&quot;", "\"").replace("&szlig;", "ß").replace("&ndash;", "-")
	title = title.replace("&#038;", "&").replace("&#8230;", "...").replace("&#8211;", "-").replace("&#8220;", "-").replace("&#8221;", "-").replace("&#8217;", "'")
	title = title.replace("&Auml;", "Ä").replace("&Uuml;", "Ü").replace("&Ouml;", "Ö").replace("&auml;", "ä").replace("&uuml;", "ü").replace("&ouml;", "ö")
	title = title.strip()
	return title


def addDir(name, **args):
	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png")
	liz.setInfo(type="Video", infoLabels={"Title": name})
	xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(**args), listitem=liz, isFolder=True)


def addChannelDir(name, iconimage, user, title, desc):
	liz = xbmcgui.ListItem(title, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": desc})
	liz.addContextMenuItems([
		build_context_entry(30026, target='playChannel', user=user),
		build_context_entry(30002, target='addChannel', user=user, name=name, thumb=iconimage),
	])
	xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(target='showSortSelection', user=user), listitem=liz, isFolder=True)


def index():
	addDir(translation(30001), target='myChannels')
	addDir(translation(30016), target='listPopular')
	addDir(translation(30006), target='search')
	liz = xbmcgui.ListItem("VidStatsX.com", iconImage="DefaultFolder.png", thumbnailImage=iconVSX)
	liz.setInfo(type="Video", infoLabels={"Title": "VidStatsX.com"})
	xbmcplugin.addDirectoryItem(handle=pluginhandle, url="plugin://plugin.video.vidstatsx_com", listitem=liz, isFolder=True)
	xbmcplugin.endOfDirectory(pluginhandle)


def myChannels():
	xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
	categories = set()
	for name, user, thumb, category in read_channels():
		if category == "NoCat":
			liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=thumb)
			liz.setInfo(type="Video", infoLabels={"Title": name})
			liz.addContextMenuItems([
				build_context_entry(30026, target='playChannel', user=user),
				build_context_entry(30024, target='addChannel', user=user, name=name, thumb=thumb),
				build_context_entry(30003, target='removeChannel', user=user),
			])
			xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(target='showSortSelection', user=user), listitem=liz, isFolder=True)
		elif category not in categories:
			categories.add(category)
			liz = xbmcgui.ListItem('- ' + category, iconImage="DefaultFolder.png")
			liz.setInfo(type="Video", infoLabels={"Title": category})
			liz.addContextMenuItems([
				build_context_entry(30009, target='removeCat', category=category),
				build_context_entry(30012, target='renameCat', category=category),
			])
			xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(target='listCat', category=category), listitem=liz, isFolder=True)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == "true":
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def listCat(category):
	xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
	for name, user, thumb, cat in read_channels():
		if cat == category:
			liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=thumb)
			liz.setInfo(type="Video", infoLabels={"Title": name})
			liz.addContextMenuItems([
				build_context_entry(30026, target='playChannel', user=user),
				build_context_entry(30024, target='addChannel', user=user, name=name, thumb=thumb),
				build_context_entry(30003, target='removeChannel', user=user),
			])
			xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(target='showSortSelection', user=user), listitem=liz, isFolder=True)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == "true":
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def showSortSelection(user):
	addDir(translation(30021), target='listVideos', user=user, orderby='published')
	addDir(translation(30022), target='listVideos', user=user, orderby='viewCount')
	addDir(translation(30023), target='listVideos', user=user, orderby='rating')
	xbmcplugin.endOfDirectory(pluginhandle)


def search():
	keyboard = xbmc.Keyboard('', translation(30006))
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		search_string = keyboard.getText().replace(" ", "+")
		listSearchChannels(search_string)


def listPopular():
	content = getUrl("https://gdata.youtube.com/feeds/api/channelstandardfeeds/most_subscribed?max-results=50&v=2")
	spl = content.split('<entry')
	for i in range(1, len(spl), 1):
		entry = spl[i]
		match = re.compile('<uri>https://gdata.youtube.com/feeds/api/users/(.+?)</uri>', re.DOTALL).findall(entry)
		user = match[0]
		match = re.compile("viewCount='(.+?)'", re.DOTALL).findall(entry)
		viewCount = match[0]
		match = re.compile("subscriberCount='(.+?)'", re.DOTALL).findall(entry)
		subscribers = match[0]
		match = re.compile("<summary>(.+?)</summary>", re.DOTALL).findall(entry)
		desc = ""
		if len(match) > 0:
			desc = match[0]
			desc = cleanTitle(desc)
		match = re.compile("<yt:userId>(.+?)</yt:userId>", re.DOTALL).findall(entry)
		thumb = "http://img.youtube.com/i/" + match[0] + "/mq1.jpg"
		addChannelDir(user, thumb, user, "[B]" + user + "[/B]  -  " + subscribers + " Subscribers", "Views: " + viewCount + "\nSubscribers: " + subscribers + "\n" + desc)
	xbmcplugin.endOfDirectory(pluginhandle)


def listSearchChannels(query, offset='1'):
	content = getUrl("https://gdata.youtube.com/feeds/api/channels?q=" + query + "&start-index=" + offset + "&max-results=50&v=2")
	match = re.compile("<openSearch:totalResults>(.+?)</openSearch:totalResults><openSearch:startIndex>(.+?)</openSearch:startIndex>", re.DOTALL).findall(content)
	maxIndex = int(match[0][0])
	startIndex = int(match[0][1])
	spl = content.split('<entry')
	for i in range(1, len(spl), 1):
		entry = spl[i]
		match = re.compile('<uri>https://gdata.youtube.com/feeds/api/users/(.+?)</uri>', re.DOTALL).findall(entry)
		user = match[0]
		match = re.compile("viewCount='(.+?)'", re.DOTALL).findall(entry)
		viewCount = match[0]
		match = re.compile("subscriberCount='(.+?)'", re.DOTALL).findall(entry)
		subscribers = match[0]
		match = re.compile("<title>(.+?)</title>", re.DOTALL).findall(entry)
		title = match[0]
		title = cleanTitle(title)
		match = re.compile("<summary>(.+?)</summary>", re.DOTALL).findall(entry)
		desc = ""
		if len(match) > 0:
			desc = match[0]
			desc = cleanTitle(desc)
		match = re.compile("<yt:userId>(.+?)</yt:userId>", re.DOTALL).findall(entry)
		thumb = "http://img.youtube.com/i/" + match[0] + "/mq1.jpg"
		addChannelDir(title, thumb, user, "[B]" + title + "[/B]  -  " + subscribers + " Subscribers", "Views: " + viewCount + "\nSubscribers: " + subscribers + "\n" + desc)
	if startIndex + 50 <= maxIndex:
		addDir(translation(30007), target='listSearchChannels', query=query, offset=int(offset) + 50)
	xbmcplugin.endOfDirectory(pluginhandle)


def listVideos(user, orderby, offset='1'):
	updateThumb(user)
	content = getUrl("http://gdata.youtube.com/feeds/api/videos?author=" + user + "&racy=include&max-results=50&start-index=" + offset + "&orderby=" + orderby + "&v=2")
	match = re.compile("<openSearch:totalResults>(.+?)</openSearch:totalResults><openSearch:startIndex>(.+?)</openSearch:startIndex>", re.DOTALL).findall(content)
	maxIndex = int(match[0][0])
	startIndex = int(match[0][1])
	spl = content.split('<entry')
	for i in range(1, len(spl), 1):
		entry = spl[i]
		match = re.compile('<yt:videoid>(.+?)</yt:videoid>', re.DOTALL).findall(entry)
		id = match[0]
		match = re.compile("viewCount='(.+?)'", re.DOTALL).findall(entry)
		viewCount = "0"
		if len(match) > 0:
			viewCount = match[0]
		match = re.compile("duration='(.+?)'", re.DOTALL).findall(entry)
		durationTemp = int(match[0])
		min = (durationTemp / 60) + 1
		sec = durationTemp % 60
		duration = str(min) + ":" + str(sec)
		match = re.compile("<author><name>(.+?)</name>", re.DOTALL).findall(entry)
		author = match[0]
		match = re.compile("<media:title type='plain'>(.+?)</media:title>", re.DOTALL).findall(entry)
		title = match[0]
		title = cleanTitle(title)
		match = re.compile("<media:description type='plain'>(.+?)</media:title>", re.DOTALL).findall(entry)
		desc = ""
		if len(match) > 0:
			desc = match[0]
			desc = cleanTitle(desc)
		match = re.compile("<published>(.+?)T", re.DOTALL).findall(entry)
		date = match[0]
		thumb = "http://img.youtube.com/vi/" + id + "/0.jpg"
		liz = xbmcgui.ListItem(title, iconImage="DefaultVideo.png", thumbnailImage=thumb)
		liz.setInfo(type="Video", infoLabels={"Title": title, "Plot": "Date: " + date + "; Views: " + viewCount + "\n" + desc, "Duration": duration, "Director": author})
		liz.setProperty('IsPlayable', 'true')
		xbmcplugin.addDirectoryItem(handle=pluginhandle, url=build_url(target='playVideo', url=id), listitem=liz)
	if startIndex + 50 <= maxIndex:
		addDir(translation(30007), target='listVideos', user=user, orderby=orderby, offset=int(offset) + 50)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == "true":
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def playVideo(url):
	listitem = xbmcgui.ListItem(path=getYoutubeUrl(url))
	return xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)


def playChannel(user):
	updateThumb(user)
	content = getUrl("http://gdata.youtube.com/feeds/api/videos?author=" + user + "&racy=include&max-results=50&start-index=1&orderby=published&v=2")
	spl = content.split('<entry')
	playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	playlist.clear()
	for i in range(1, len(spl), 1):
		try:
			entry = spl[i]
			match = re.compile('<yt:videoid>(.+?)</yt:videoid>', re.DOTALL).findall(entry)
			id = match[0]
			url = getYoutubeUrl(id)
			match = re.compile("<media:title type='plain'>(.+?)</media:title>", re.DOTALL).findall(entry)
			title = match[0]
			title = cleanTitle(title)
			listitem = xbmcgui.ListItem(title)
			playlist.add(url, listitem)
		except:
			pass
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
	xbmc.executebuiltin("Container.Refresh")
	if showMessages == "true":
		xbmc.executebuiltin('XBMC.Notification(Info:,' + translation(30019).format(channel=user) + ',5000)')
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
iconVSX = xbmc.translatePath('special://home/addons/' + addonID + '/iconVSX.png')
forceViewMode = addon.getSetting("forceView")
viewMode = str(addon.getSetting("viewMode"))
showMessages = str(addon.getSetting("showMessages"))

if not os.path.isdir(addon_work_folder):
	os.mkdir(addon_work_folder)


args = {key: (values[0] if len(values) == 1 else values) for key, values in urlparse.parse_qs(sys.argv[2][1:]).items()}
target = args.pop('target', 'index')
locals()[target](**args)

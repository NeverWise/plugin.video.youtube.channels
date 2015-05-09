#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import pickle
import re
import socket
import sys
import urllib
import urllib2

import xbmcaddon
import xbmcgui
import xbmcplugin


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


def translation(id):
	return addon.getLocalizedString(id).encode('utf-8')


def index():
	addDir(translation(30001), "", "myChannels", "")
	addDir(translation(30016), "", "listPopular", "")
	addDir(translation(30006), "", "search", "")
	addVSXDir("VidStatsX.com", "", "", iconVSX)
	xbmcplugin.endOfDirectory(pluginhandle)


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


def myChannels():
	xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
	categories = set()
	for name, user, thumb, category in read_channels():
		if category == "NoCat":
			addChannelFavDir(name, user + "#1", 'showSortSelection', thumb, user)
		elif category not in categories:
			categories.add(category)
			addCatMainDir("- " + category, category, "listCat", "")
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == "true":
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def listCat(cat):
	xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
	for name, user, thumb, category in read_channels():
		if category == cat:
			addCatDir(name, user + "#1", 'showSortSelection', thumb, user, category)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == "true":
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def showSortSelection(url):
	addDir(translation(30021), url + "#published", "listVideos", "")
	addDir(translation(30022), url + "#viewCount", "listVideos", "")
	addDir(translation(30023), url + "#rating", "listVideos", "")
	xbmcplugin.endOfDirectory(pluginhandle)


def search():
	keyboard = xbmc.Keyboard('', translation(30006))
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		search_string = keyboard.getText().replace(" ", "+")
		listSearchChannels(search_string + "#1")


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
		addChannelDir("[B]" + user + "[/B]  -  " + subscribers + " Subscribers", user + "#1", 'showSortSelection', thumb, user, "Views: " + viewCount + "\nSubscribers: " + subscribers + "\n" + desc)
	xbmcplugin.endOfDirectory(pluginhandle)


def listSearchChannels(params):
	spl = params.split("#")
	search = spl[0]
	index = spl[1]
	content = getUrl("https://gdata.youtube.com/feeds/api/channels?q=" + search + "&start-index=" + index + "&max-results=50&v=2")
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
		addChannelDir("[B]" + title + "[/B]  -  " + subscribers + " Subscribers", user + "#1", 'showSortSelection', thumb, user, "Views: " + viewCount + "\nSubscribers: " + subscribers + "\n" + desc)
	if startIndex + 50 <= maxIndex:
		addDir(translation(30007), search + "#" + str(int(index) + 50), 'listSearchChannels', "")
	xbmcplugin.endOfDirectory(pluginhandle)


def updateThumb(edit_user):
	def newthumb():
		content = getUrl("http://www.youtube.com/user/" + edit_user)
		match = re.search('\'CHANNEL_ID\', "UC(.+?)"', content)
		return "http://img.youtube.com/i/" + match.group(0) + "/mq1.jpg"
	write_channels([(name, user, newthumb() if user == edit_user and thumb == "DefaultFolder.png" else thumb, category) for name, user, thumb, category in read_channels()])


def listVideos(params):
	spl = params.split("#")
	user = spl[0]
	index = spl[1]
	orderby = spl[2]
	updateThumb(user)
	content = getUrl("http://gdata.youtube.com/feeds/api/videos?author=" + user + "&racy=include&max-results=50&start-index=" + index + "&orderby=" + orderby + "&v=2")
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
		addLink(title, id, 'playVideo', thumb, "Date: " + date + "; Views: " + viewCount + "\n" + desc, duration, author)
	if startIndex + 50 <= maxIndex:
		addDir(translation(30007), user + "#" + str(int(index) + 50) + "#" + orderby, 'listVideos', "")
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode == "true":
		xbmc.executebuiltin('Container.SetViewMode(' + viewMode + ')')


def playVideo(youtubeID):
	url = getYoutubeUrl(youtubeID)
	listitem = xbmcgui.ListItem(path=url)
	return xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)


def getYoutubeUrl(youtubeID):
	return ("plugin://video/YouTube/?path=/root/video&action=play_video&videoid=" if xbox else "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=") + youtubeID


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


def addChannel(args):
	args = args.replace("[B]", "").replace("[/B]", "")
	match = re.compile('(.+?)#(.+?)#(.+?)#', re.DOTALL).findall(args)
	name = match[0][0]
	id = match[0][1]
	thumb = match[0][2]
	if "  -  " in name:
		name = name[:name.find("  -  ")]
	if "  -  " in id:
		id = id[:id.find("  -  ")]
	while True:
		playlists = [translation(30027)] + get_categories() + ["- " + translation(30005)]
		dialog = xbmcgui.Dialog()
		index = dialog.select(translation(30004), playlists)
		if index >= 0:
			pl = playlists[index]
			if pl == playlists[-1]:
				addon.openSettings()
				continue
			elif pl != "":
				if pl == translation(30027):
					pl = "NoCat"
				channels = set(read_channels())
				channels.add((name, id, thumb, pl))
				write_channels(channels)
				if showMessages == "true":
					xbmc.executebuiltin('XBMC.Notification(Info:,' + translation(30018).format(channel=name) + ',5000)')
		break


def addToCat(args):
	args = args.replace("[B]", "").replace("[/B]", "")
	match = re.compile('(.+?)#(.+?)#(.+?)#', re.DOTALL).findall(args)
	name = match[0][0]
	id = match[0][1]
	thumb = match[0][2]
	if "  -  " in name:
		name = name[:name.find("  -  ")]
	if "  -  " in id:
		id = id[:id.find("  -  ")]
	while True:
		playlists = get_categories() + ["- " + translation(30005)]
		dialog = xbmcgui.Dialog()
		index = dialog.select(translation(30004), playlists)
		if index >= 0:
			pl = playlists[index]
			if pl == playlists[-1]:
				addon.openSettings()
				continue
			elif pl != "":
				channels = set(read_channels())
				channels.add((name, id, thumb, pl))
				write_channels(channels)
				if showMessages == "true":
					xbmc.executebuiltin('XBMC.Notification(Info:,' + translation(30018).format(channel=name) + ',5000)')
				xbmc.executebuiltin("Container.Refresh")
		break


def removeChannel(remove_user):
	write_channels([channel for channel in read_channels() if channel[1] != remove_user])
	xbmc.executebuiltin("Container.Refresh")
	if showMessages == "true":
		xbmc.executebuiltin('XBMC.Notification(Info:,' + translation(30019).format(channel=name) + ',5000)')
	xbmc.executebuiltin("Container.Refresh")


def removeCat(cat):
	if xbmcgui.Dialog().ok('Info:', translation(30010) + "?"):
		write_channels([channel for channel in read_channels() if channel[3] != cat])
		xbmc.executebuiltin("Container.Refresh")


def renameCat(cat):
	keyboard = xbmc.Keyboard(cat, translation(30011) + " " + cat)
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		newName = keyboard.getText()
		write_channels([(oname, ouser, othumb, newName if ocategory == cat else ocategory) for oname, ouser, othumb, ocategory in read_channels()])
		xbmc.executebuiltin("Container.Refresh")


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


def addLink(name, url, mode, iconimage, desc="", duration="", author=""):
	u = sys.argv[0] + "?url=" + urllib.quote_plus(url) + "&mode=" + str(mode)
	liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
	liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": desc, "Duration": duration, "Director": author})
	liz.setProperty('IsPlayable', 'true')
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz)


def addDir(name, url, mode, iconimage):
	u = sys.argv[0] + "?url=" + urllib.quote_plus(url) + "&mode=" + str(mode)
	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo(type="Video", infoLabels={"Title": name})
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)


def addVSXDir(name, url, mode, iconimage):
	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo(type="Video", infoLabels={"Title": name})
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url="plugin://plugin.video.vidstatsx_com", listitem=liz, isFolder=True)


def addChannelDir(name, url, mode, iconimage, user, desc=""):
	u = sys.argv[0] + "?url=" + urllib.quote_plus(url) + "&mode=" + str(mode)
	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": desc})
	liz.addContextMenuItems([
		(translation(30026), 'XBMC.RunPlugin(plugin://' + addonID + '/?mode=playChannel&url=' + user + ')',),
		(translation(30002), 'RunPlugin(plugin://' + addonID + '/?mode=addChannel&url=' + urllib.quote_plus(name + "#" + user + "#" + iconimage + "#") + ')',)
	])
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)


def addChannelFavDir(name, url, mode, iconimage, user):
	u = sys.argv[0] + "?url=" + urllib.quote_plus(url) + "&mode=" + str(mode)
	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo(type="Video", infoLabels={"Title": name})
	liz.addContextMenuItems([
		(translation(30026), 'XBMC.RunPlugin(plugin://' + addonID + '/?mode=playChannel&url=' + user + ')',),
		(translation(30024), 'RunPlugin(plugin://' + addonID + '/?mode=addToCat&url=' + urllib.quote_plus(name + "#" + user + "#" + iconimage + "#") + ')',),
		(translation(30003), 'RunPlugin(plugin://' + addonID + '/?mode=removeChannel&url=' + urllib.quote_plus(user) + ')',)
	])
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)


def addCatMainDir(name, url, mode, iconimage):
	u = sys.argv[0] + "?url=" + urllib.quote_plus(url) + "&mode=" + str(mode)
	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo(type="Video", infoLabels={"Title": name})
	liz.addContextMenuItems([
		(translation(30009), 'RunPlugin(plugin://' + addonID + '/?mode=removeCat&url=' + urllib.quote_plus(url) + ')',),
		(translation(30012), 'RunPlugin(plugin://' + addonID + '/?mode=renameCat&url=' + urllib.quote_plus(url) + ')',)
	])
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)


def addCatDir(name, url, mode, iconimage, user, cat):
	u = sys.argv[0] + "?url=" + urllib.quote_plus(url) + "&mode=" + str(mode)
	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo(type="Video", infoLabels={"Title": name})
	liz.addContextMenuItems([
		(translation(30026), 'XBMC.RunPlugin(plugin://' + addonID + '/?mode=playChannel&url=' + user + ')',),
		(translation(30003), 'RunPlugin(plugin://' + addonID + '/?mode=removeChannel&url=' + urllib.quote_plus(user) + ')',)
	])
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)


def parameters_string_to_dict(parameters):
	''' Convert parameters encoded in a URL to a dict. '''
	paramDict = {}
	if parameters:
		paramPairs = parameters[1:].split("&")
		for paramsPair in paramPairs:
			paramSplits = paramsPair.split('=')
			if (len(paramSplits)) == 2:
				paramDict[paramSplits[0]] = paramSplits[1]
	return paramDict


params = parameters_string_to_dict(sys.argv[2])
mode = params.get('mode')
url = params.get('url')
if type(url) == type(str()):
	url = urllib.unquote_plus(url)

if mode == 'search':
	search()
elif mode == 'myChannels':
	myChannels()
elif mode == 'listPopular':
	listPopular()
elif mode == 'listSearchChannels':
	listSearchChannels(url)
elif mode == 'showSortSelection':
	showSortSelection(url)
elif mode == 'listVideos':
	listVideos(url)
elif mode == 'listCat':
	listCat(url)
elif mode == 'playVideo':
	playVideo(url)
elif mode == 'playChannel':
	playChannel(url)
elif mode == 'favourites':
	favourites(url)
elif mode == 'addChannel':
	addChannel(url)
elif mode == 'addToCat':
	addToCat(url)
elif mode == 'removeChannel':
	removeChannel(url)
elif mode == 'removeCat':
	removeCat(url)
elif mode == 'renameCat':
	renameCat(url)
else:
	index()

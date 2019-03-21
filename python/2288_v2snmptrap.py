#!/usr/bin/env python
#coding=utf-8

import urllib,urllib2,re,cookielib,json,sys,getopt,os
from time import ctime,sleep



class CH242():

	def __init__(self, info):

		self.info = info
		self.opener = None
		self.data = ''
		self.sender = '/usr/local/zabbix_proxy/bin/zabbix_sender'
		self.login()
		self.set()


	def login(self):
		url = 'https://{ip}/goform/Login'.format(ip=self.info['ip'])
		data = {
			'lang': 'cn',
			'UserName': self.info['user'],
			'Password': self.info['password'],
			'authenticateType': 0,
			'domain': 0,
			'forward_url': '',
			'forward_ip': '',
			'forward_userAgent':''
		}
		cookie = cookielib.CookieJar()
		cookie_handler = urllib2.HTTPCookieProcessor(cookie)
		self.opener = urllib2.build_opener(cookie_handler)
		self.opener.addheaders = [("Content-Type","application/x-www-form-urlencoded"),("Upgrade-Insecure-Requests",1),("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36")]
		params = urllib.urlencode(data)
		req = urllib2.Request(url,params)
		self.opener.open(req)

	def set(self):
		url = "https://"+ self.info['ip'] +"/snmptrap.asp"
		response = self.opener.open(url)
		content = response.read()
		regex = r"session_token\"\s+value=\"(.*?)\""
		pattern = re.compile(regex,re.M|re.S)
		res = pattern.findall(content)
		token =  res[0]

		url = 'https://{ip}/goform/formTrapManager'.format(ip=self.info['ip'])
		data = {
			'session_token': token,
			'trapsetdisable': 'on',
			'alarmlevel': 0,
			'trapversion': 2,
			'trapmode': 1,
			'trapServerIdentity': 0,
			'separator1': '',
			'formattxt1': 'Time,Sensor,Event,Severity,Event Code',
			'showkeyflag1': 1,
			'trapport1': 162,
			'separator2': '',
			'formattxt2': 'Time,Sensor,Event,Severity,Event Code',
			'showkeyflag2': 1,
			'enabledcheck2': 'on',
			'ipaddr2': '10.142.88.30',
			'trapport2': 162,
			'separator3': '',
			'formattxt3': 'Time,Sensor,Event,Severity,Event Code',
			'showkeyflag3': 1,
			'ipaddr3': '',
			'trapport3': 162,
			'separator4': '',
			'formattxt4': 'Time,Sensor,Event,Severity,Event Code',
			'showkeyflag4': 1,
			'ipaddr4': '',
			'trapport4': 162,
		}
		params = urllib.urlencode(data)
		req = urllib2.Request(url,params)
		self.opener.open(req)



	def hardware(self):
		response = self.opener.open("https://"+ self.info['ip'] +"/allconfig.asp") 
		content = response.read()
		self.cpu(content)



if __name__=='__main__':
	data = {
		'user' : 'root',
		'password' : 'Huawei12#$'
	}
	#CH242(data)
	f = open('./15.txt','r')
	all = f.readlines()
	for x in all:
		ip = x.split(',')[0]
		data['ip'] = ip 
		print ip
		CH242(data)


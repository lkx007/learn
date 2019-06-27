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
		self.hardware()
		#退出
		self.sendToZabbix()


	def login(self):
		url = 'https://{ip}/goform/Login'.format(ip=self.info['ip'])
		data = {
			'lang': 'cn',
			'UserName': self.info['user'],
			'Password': self.info['password'],
			'authenticateType': 0,
			'domain': 0
		}
		cookie = cookielib.CookieJar()
		cookie_handler = urllib2.HTTPCookieProcessor(cookie)
		self.opener = urllib2.build_opener(cookie_handler)
		self.opener.addheaders = [("Content-Type","application/x-www-form-urlencoded"),("Upgrade-Insecure-Requests",1),("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36")]
		params = urllib.urlencode(data)
		req = urllib2.Request(url,params)
		self.opener.open(req)
		for item in cookie:
			print ('Name = '+item.name)
			print ('Value = '+item.value


	def hardware(self):
		response = self.opener.open("https://"+ self.info['ip'] +"/allconfig.asp") 
		content = response.read()
		self.cpu(content)


	def cpu(self,content):
		regex = r"CPULeftStr = \"(.*?)\";"
		pattern = re.compile(regex,re.M|re.S)
		cpuNameString = pattern.findall(content)
		cpuNames = []
		if cpuNameString:
			cpuNames = cpuNameString[0].split("|")

		#cpu详细信息
		regex = r"CPURightStr = \"(.*?)\";"
		pattern = re.compile(regex,re.M|re.S)
		cpuDescString = pattern.findall(content)
		cpuDescs = []
		if cpuDescString:
			cpuDescs = cpuDescString[0].split("|")
		#cpu 自动发现和信息
		newCpuNames = []
		if cpuNames and cpuDescs:
			for k,v in enumerate(cpuNames):
				self.complateData('cpu.name[{id}]'.format(id=v),v)
				tmp = cpuDescs[k].split()
				self.complateData('cpu.type[{id}]'.format(id=v),tmp[1])
				self.complateData('cpu.model[{id}]'.format(id=v),tmp[3])
				self.complateData('cpu.mfc[{id}]'.format(id=v),tmp[0])
				self.complateData('cpu.frequency[{id}]'.format(id=v),tmp[6].replace('GHz',''))
				newCpuNames.append( '{"{#NAME}":"%s"}'% (v.strip()))

		discovery   = self.j(newCpuNames)
		self.complateData('cpu',discovery) # 自动发现


	def j(self,output):
		json = []
		json.append('{"data":[')
		for i, v in enumerate( output ):
			if i < len(output)-1:
				json.append(v+',')
		else:
			json.append(v)
		json.append(']}')

		jsonString = ''.join(json)
		return jsonString


	def complateData(self,key,value):
		if self.data:
			self.data += '\n"{0}" \t "{1}" \t {2}'. format(self.info['host'],key,value)
		else:
			self.data += '"{0}"  \t "{1}" \t  {2}' . format(self.info['host'],key,value)

	def sendToZabbix(self):
		file = '/tmp/'+ self.info['ip']
		f = open(file,'w')
		f.write(self.data)
		f.close()

		command = "{sender} -z {proxy} -i {file}".format(sender=self.sender,proxy=self.info['proxy'],file=file)
		os.popen(command)

		#os.remove(file)




def myHelp():
	print "使用实例"
	print "python /usr/local/src/ch242.py  --ip ip --user user --password password --host host --proxy proxy"
	exit()

if __name__=='__main__':
	data = {}
	opts, args = getopt.gnu_getopt(sys.argv[1:], "-hi:u:p:h:P:", ["help","ip=", "user=",  "password=", "host=","proxy="])
	for k,v in opts:
		if k in ('-h','--help'):
			myHelp()
		elif k in ('-i','--ip'):
			data['ip'] = v
		elif k in ('-u','--user'):
			data['user'] = v
		elif k in ('-p','--password'):
			data['password'] = v
		elif k in ('-h','--host'):
			data['host'] = v
		elif k in ('-P','--proxy'):
			data['proxy'] = v

	if len(data)<5:
		print "参数有误"
		myHelp()

	CH242(data)

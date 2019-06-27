#!/usr/bin/env python
#coding=utf-8
import urllib.request as  request
import re,json,os,sys


class Tjj(object):
	"""docstring for Tjj"""
	def __init__(self, arg):
		self.json = ''
		self.items = []
		self.info = arg
		self.data = ''
		self.sender = '/usr/local/zabbix/bin/zabbix_sender'
		self.file = self.info['host']

	def run(self):
		if(self.getHtml()):
			self.handData()
			self.save()
			#self.sendToZabbix()
			#print(self.data)
		else:
			print('error')

	def sendToZabbix(self):
		command = "{sender} -z {proxy} -i {file}".format(sender=self.sender,proxy='127.0.0.1',file=self.file)
		os.popen(command)
		#os.remove()

	def save(self):
		f = open(self.file,'w')
		f.write(self.data)
		f.close()



	def handData(self):
		if self.items:
			names = []
			for x in self.items:
				name = x[0]
				# name = name.encode('utf-8')
				# print(type(float(x[4])))
				names.append('{"{#NAME}":%s}'% (name))
				self.combine("national[{id}]".format(id=name),name)
				self.combine("people[{id}]".format(id=name),int(x[1]))
				self.combine("man[{id}]".format(id=name),int(x[2]))
				self.combine("woman[{id}]".format(id=name),int(x[3]))
				self.combine("precent[{id}]".format(id=name),float(x[4]))


			json = []
			json.append('{"data":[')
			for i, v in enumerate( names ):
				if i < len(names)-1:
					json.append(v+',')
				else:
					json.append(v)
			json.append(']}')
			json_string = ''.join(json)
			#print(json_string)
			self.combine("national",json_string)

	def combine(self,key,value):
		if self.data:
			self.data += '\n"{0}" \t "{1}" \t {2}'. format(self.info['host'],key,value)
		else:
			self.data += '"{0}"  \t "{1}" \t  {2}' . format(self.info['host'],key,value)

	def getHtml(self):
		fd = request.urlopen(self.info['url'])
		html = fd.read().decode()
		regex = r'<tbody.*?>(.*?)<\/tbody>'
		pattern = re.compile(regex,re.M|re.S)
		content = pattern.findall(html)
		itemsRegex = r'<tr.*?>[\n\r].*?<td.*?>\s?(.*?)<\/td>[\n\r].*?<td.*?>(.*?)<\/td>[\n\r].*?<td.*?>(.*?)<\/td>[\n\r].*?<td.*?>(.*?)<\/td>[\n\r].*?<td.*?>(.*?)<\/td>[\n\r].*?<\/tr>'
		itemPattern = re.compile(itemsRegex,re.M|re.S)
		if content:
			self.items = itemPattern.findall(content[0])
			self.items = self.items[4:]
			return True




if __name__ == '__main__':
	url = 'http://tjj.gz.gov.cn/gzstats/pchb_cydc/201704/2eabfc08800e45a7bcc2a8dd8fdeaf54.shtml'
	tjj = Tjj({"url":url,'host':'test_allen'})
	tjj.run()












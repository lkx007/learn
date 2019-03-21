#!/usr/bin/env python 
#coding=utf-8

import pywbem,getopt, sys, datetime, time, calendar, json,os,math



class Vsp:
	"""docstring for Vsp"""
	conn = None
	namespace = 'root/hitachi/smis'
	zabbix_sender = '/usr/local/zabbix_proxy.bak/bin/zabbix_sender'
	port = 100
	cache = {}
	cacheFile = None

	def __init__(self, ip,user,pwd,host,port,proxy,fun):
		self.ip = ip
		self.user = user
		self.pwd = pwd
		self.host = host
		self.proxy = proxy
		self.port = port

		self.conn = self.connect()


		self.cacheFile = '/tmp/hds/hds' + self.ip
		if os.path.exists(self.cacheFile):
			self.cache = json.load( open(self.cacheFile, 'r') )
		else:
			f = open(self.cacheFile,'w')
			f.write('{}')
			f.close()

		fun = 'self.' + fun
		#eval(fun)()
		self.hostGroupMsg()
		print "采集完成"


	def msg(self):
		self.hostMsg()
		self.poolMsg()
		self.raidMsg()
		self.lunMsg()
		self.diskMsg()
		self.fcportMsg()
		self.hostGroupMsg()

	def performance(self):
		self.fcSpeedPerf()
		self.lunPerf()
		self.saveCache()


	def connect(self):
		 return pywbem.WBEMConnection('https://'+self.ip, (self.user, self.pwd), Vsp.namespace,None,None,None,True)

	def send_to_zabbix(self,key,value):
		command = "{zabbix_sender}  -z '{proxy}' -p {port} -s '{host}' -k {key} -o  '{value}'".format(zabbix_sender=Vsp.zabbix_sender,proxy=self.proxy,port=self.port,host=self.host,key=key,value=value)
		os.popen(command)
		



	def poolMsg(self):
		print "采集POOL信息"
		data = self.conn.EnumerateInstances('HITACHI_ThinProvisioningPool')
		for x in data:
			if len(x):
				id = x['ElementName'] 
				self.send_to_zabbix('pool.name[{id}]'.format(id=id), x['ElementName']) #
				self.send_to_zabbix('pool.status[{id}]'.format(id=id), x['HealthState']) #
				self.send_to_zabbix('pool.consist[{id}]'.format(id=id), x['ConsistsOf']) #
				self.send_to_zabbix('pool.usage[{id}]'.format(id=id), x['Usage']) #
				self.send_to_zabbix('pool.capacity.size.reserved[{id}]'.format(id=id), x['ReservedSpace']) #
				self.send_to_zabbix('pool.capacity.size.free[{id}]'.format(id=id), x['RemainingManagedSpace']) # 
				self.send_to_zabbix('pool.capacity.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) #

	def raidMsg(self):
		print "采集RAID信息"
		data = self.conn.EnumerateInstances('HITACHI_StoragePool')
		for x in data:
			if len(x):
				arr = x['ElementName'].split('.')
				id =  arr[-1]
				self.send_to_zabbix('raid.size.free[{id}]'.format(id=id), x['RemainingManagedSpace']) 
				self.send_to_zabbix('raid.name[{id}]'.format(id=id), x['ElementName'])
				self.send_to_zabbix('raid.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) 
				self.send_to_zabbix('raid.status[{id}]'.format(id=id), x['HealthState']) 

		data = self.conn.EnumerateInstances('HITACHI_ArrayGroup')
		for x in data:
			if len(x):
				id = '-' .join ( x['DeviceID'].split('.') )
				self.send_to_zabbix('raid.block.size[{id}]'.format(id=id), x['BlockSize']) 
				self.send_to_zabbix('raid.number.blocks[{id}]'.format(id=id), x['NumberOfBlocks']) 
				self.send_to_zabbix('raid.level[{id}]'.format(id=id), x['ErrorMethodology']) 

	def lunMsg(self):
		print "采集LUN信息"
		data = self.conn.EnumerateInstances('HITACHI_StorageVolume')
		for x in data:
			if len(x):
				id = x['DeviceID']
				self.send_to_zabbix('lun.id[{id}]'.format(id=id), x['DeviceID']) 
				self.send_to_zabbix('lun.level[{id}]'.format(id=id), x['ErrorMethodology']) 
				self.send_to_zabbix('lun.local[{id}]'.format(id=id), x['Caption']) 
				self.send_to_zabbix('lun.name[{id}]'.format(id=id), x['ElementName']) 
				self.send_to_zabbix('lun.size.total[{id}]'.format(id=id), x['NumberOfBlocks'] * x['BlockSize']) 
				self.send_to_zabbix('lun.status[{id}]'.format(id=id), x['HealthState']) 

	def diskMsg(self):
		print "采集DISK信息"
		data = self.conn.EnumerateInstances('HITACHI_DiskDrive')
		for x in data:
			if len(x):
				id = x['DeviceID']
				usage = 'spare'
				if 0 == x['DeviceID'].find('-'):
					usage = 'data'
				self.send_to_zabbix('disk.local[{id}]'.format(id=id), x['Location'])
				self.send_to_zabbix('disk.usage[{id}]'.format(id=id), usage)
				self.send_to_zabbix('disk.size.total[{id}]'.format(id=id), x['MaxMediaSize'])
				self.send_to_zabbix('disk.descript[{id}]'.format(id=id), ',' . join( x['CapabilityDescriptions']))
				self.send_to_zabbix('disk.status[{id}]'.format(id=id), x['HealthState'])
				self.send_to_zabbix('disk.type[{id}]'.format(id=id), x['DiskType'])
				if x.__contains__('RPM'):
					self.send_to_zabbix('disk.speed[{id}]'.format(id=id), x['RPM'])

		data =  self.conn.EnumerateInstances('HITACHI_DiskDriveView')
		for x in data:
			if len(x):
				id = x['SEDeviceID']
				#self.send_to_zabbix('disk.part.number[{id}]'.format(id=id), x['PPPartNumber']) #采集结果没有
				self.send_to_zabbix('disk.mfc[{id}]'.format(id=id), x['PPManufacturer'])
				self.send_to_zabbix('disk.blocks.size[{id}]'.format(id=id), x['SEBlockSize'])
				self.send_to_zabbix('disk.blocks[{id}]'.format(id=id), x['SENumberOfBlocks'])

	def fcportMsg(self):
		print "采集FC PORT信息"
		data = self.conn.EnumerateInstances('HITACHI_FCPort')
		for x in data:
			if len(x):
				id = x['DeviceID']
				#self.send_to_zabbix('fccon.fc4.type[{id}]'.format(id=id), x['ActiveFC4Types'])
				self.send_to_zabbix('fccon.port.number[{id}]'.format(id=id), x['PortNumber'])
				self.send_to_zabbix('fccon.speed[{id}]'.format(id=id), x['Speed'])
				self.send_to_zabbix('fccon.port.wwn[{id}]'.format(id=id), x['PermanentAddress'])
				self.send_to_zabbix('fccon.port.type[{id}]'.format(id=id), x['PortType'])
				self.send_to_zabbix('fccon.id[{id}]'.format(id=id), x['DeviceID'])
				self.send_to_zabbix('fccon.type[{id}]'.format(id=id), x['LinkTechnology'])
				self.send_to_zabbix('fccon.name[{id}]'.format(id=id), x['ElementName'])
				self.send_to_zabbix('fccon.status[{id}]'.format(id=id), x['HealthState'])

	def hostGroupMsg(self):
		print "采集HOST GROUP信息"
		#主机组和FC端口的关系  [主机组ID] = [端口ID]
		release = self.getHgReleasePortDist()
		#端口信息 [id]=[fc]
		fcDist = self.getFcDist()

		data = self.conn.EnumerateInstances('HITACHI_SCSIProtocolController')
		for x in data:
			if len(x):
				id = x['DeviceID']
				self.send_to_zabbix('host.group.id[{id}]'.format(id=id), x['DeviceID'])
				self.send_to_zabbix('host.group.model[{id}]'.format(id=id), x['HostMode'])
				self.send_to_zabbix('host.group.alias[{id}]'.format(id=id), x['ElementName'])

				if release.__contains__(id):#用组ID找出FC端口ID
					fcId = release[id]
					if fcDist.__contains__(fcId):#FC端口ID找出端口信息
						fc = fcDist[fcId]
						self.send_to_zabbix('host.group.fccon.wwn[{id}]'.format(id=id), fc['DeviceID'])
						self.send_to_zabbix('host.group.fccon.name[{id}]'.format(id=id), fc['ElementName'])


	def hostMsg(self):
		print "采集HOST信息"
		release = self.conn.EnumerateInstances('HITACHI_AuthorizedTarget')
		hostGroupDict = self.handHostGroup()
		data = self.conn.EnumerateInstances('HITACHI_AuthorizedPrivilege')

		hgReleasePortDist = self.getHgReleasePortDist()
		fcDist = self.getFcDist()

		for x in data:
			arr = x['InstanceID'].split(' ')
			id = arr[-1]
			arr = x['InstanceID'].split('.')
			wwn = arr[-1]
			self.send_to_zabbix('host.id[{id}]'.format(id=id), x['InstanceID'])
			self.send_to_zabbix('host.wwn[{id}]'.format(id=id), wwn)
			# group info 
			hg = self.hostWithGroup(release,hostGroupDict,x['InstanceID'])
			if len(hg):
				self.send_to_zabbix('host.group.name[{id}]'.format(id=id), hg['ElementName'])
				# fc信息
				fc = self.hostWithFcport(hgReleasePortDist,fcDist,hg['DeviceID'])
				if len(fc):
					self.send_to_zabbix('host.port.name[{id}]'.format(id=id), fc['ElementName']) #fc name 
					self.send_to_zabbix('host.port.wwn[{id}]'.format(id=id), fc['DeviceID']) #fc wwn 

	#把主机组数据组装成 [主机组id] = [主机组信息] 的字典
	def handHostGroup(self):
		hostGroup = self.conn.EnumerateInstances('HITACHI_SCSIProtocolController')
		hdist = {}
		for x in hostGroup:
			id = x['DeviceID']
			hdist[id] = x
		return hdist

	# 根据主机ID 返回主机组信息
	'''
	release		主机和主机组的关系
	hostGroupDict	处理后的主机组信息
	hostId      主机ID 
	'''
	def hostWithGroup(self,release,hostGroupDict,hostId):
		hg = None
		gid = None
		if len(hostId) and len(release):
			for r in release:
				if hostId == r['Privilege']['InstanceID']:
					gid = r['TargetElement']['DeviceID']
					break
		if len(gid) and gid in hostGroupDict:
			hg = hostGroupDict[gid]
		return hg

	# 主机组和FC端口的关系  [主机组ID] = [端口ID]
	def getHgReleasePortDist(self):
		hgReleasePortDist = {}
		release = self.conn.EnumerateInstances('HITACHI_SCSIPCForFCPort')
		for x in release:
			if len(x):
				id = x['Antecedent']['DeviceID']  #主机组
				hgReleasePortDist[id] = x['Dependent']['DeviceID']  # 端口
		return hgReleasePortDist

	#把FC 端口信息组装成字典 [id]=[fc]
	def getFcDist(self):
		data = self.conn.EnumerateInstances('HITACHI_FCPort')
		fcDist = {}
		if len(data):
			for x in data:
				id = x['DeviceID']
				fcDist[id] = x
		return fcDist

	"""
		根据主机ID和主机组ID,返回端口信息
		hgReleasePortDist	主机组和端口关系
		fcport 				端口
		groupId 			主机组ID
		hostId 				主机ID
	"""
	def hostWithFcport(self,hgReleasePortDist,fcDist,groupId):
		fc = None #[] 一个主机组应该只对应一个端口
		if len(hgReleasePortDist) and len(fcDist) and len(groupId):
			for x in hgReleasePortDist:
				if groupId == x:
					id = hgReleasePortDist[x]  #与组对应的端口信息ID
					fc = fcDist[id]
		return fc



	"""
	动态数据
	"""

	"""fc端口流量信息
	"""
	def fcSpeedPerf(self):
		print "采集FC PERF信息"
		#旧的
		old = None
		if self.cache and self.cache.__contains__('fcport'):
			old = self.cache['fcport']
		#新的
		data = self.conn.EnumerateInstances('HITACHI_BlockStatisticalDataFCPort')
		new = {}
		if len(data):
			timestamp = calendar.timegm(data[0]['StatisticTime'].datetime.timetuple())
			for x in data:
				id = x['InstanceID'].split('.')[-1]
				tmp = {}
				tmp['timestamp'] = timestamp
				tmp['KBytesTransferred'] = x['KBytesTransferred'] #总流量
				tmp['TotalIOs'] = x['TotalIOs'] #总IO/S
				new[id] = tmp
				#计算
				if old and old.__contains__(id) and timestamp-old[id]['timestamp'] > 0:
					KBytesTransferred = ( x['KBytesTransferred'] - old[id]['KBytesTransferred'] ) / (timestamp-old[id]['timestamp'])
					#发送到ZABBIX
					self.send_to_zabbix('ifHcoctetsOnInterfacesPersecond[{id}]'.format(id=id), KBytesTransferred )
		self.cache['fcport'] = new

		"""
		lun I/O信息
		"""
	def lunPerf(self):
		print "采集LUN IO信息"
		#旧的
		old = None
		if self.cache and self.cache.__contains__('lun'):
			old = self.cache['lun']
		#新的
		data = self.conn.EnumerateInstances('HITACHI_BlockStatisticalDataStorageVolume')
		new = {}
		if len(data):
			timestamp = calendar.timegm(data[0]['StatisticTime'].datetime.timetuple())
			for x in data:
				id = x['InstanceID'].split('.')[-1]
				tmp = {}
				tmp['timestamp'] = timestamp
				tmp['KBytesTransferred'] = x['KBytesTransferred'] #总流量
				tmp['TotalIOs'] = x['TotalIOs'] #总IO/S  The total number of ReadIOs, ReadHitIOs, WriteIOs and WriteHitIOs of a volume   每秒输入输出次数,指的是系统在单位时间内能处理的最大的I/O频度
				tmp['ReadIOs'] = x['ReadIOs']
				tmp['ReadHitIOs'] = x['ReadHitIOs']
				tmp['WriteIOs'] = x['WriteIOs']
				tmp['WriteHitIOs'] = x['WriteHitIOs']
				new[id] = tmp
				#计算
				if old and old.__contains__(id) and timestamp-old[id]['timestamp'] > 0:
					KBytesTransferred = int((x['KBytesTransferred'] - old[id]['KBytesTransferred']) / (timestamp-old[id]['timestamp']))
					TotalIOs = int((x['TotalIOs'] - old[id]['TotalIOs']) / (timestamp-old[id]['timestamp']))
					ReadIOs = int((x['ReadIOs'] - old[id]['ReadIOs']) / (timestamp-old[id]['timestamp']))
					ReadHitIOs = int((x['ReadHitIOs'] - old[id]['ReadHitIOs']) / (timestamp-old[id]['timestamp']))
					WriteIOs = int((x['WriteIOs'] - old[id]['WriteIOs']) / (timestamp-old[id]['timestamp']))
					WriteHitIOs = int((x['WriteHitIOs'] - old[id]['WriteHitIOs']) / (timestamp-old[id]['timestamp']))
					#发送到ZABBIX
					self.send_to_zabbix('lun.rw.rate[{id}]'.format(id=id), KBytesTransferred )
					self.send_to_zabbix('lun.rw.io.rate[{id}]'.format(id=id), TotalIOs )
					self.send_to_zabbix('lun.read.io.rate[{id}]'.format(id=id), ReadIOs )
					self.send_to_zabbix('lun.write.io.rate[{id}]'.format(id=id), WriteIOs )
					#缓存命中率
					if ReadIOs > 0:
						self.send_to_zabbix('lun.read.io.hit[{id}]'.format(id=id), ReadHitIOs/ReadIOs*100)
					if WriteIOs > 0:
						self.send_to_zabbix('lun.write.io.hit[{id}]'.format(id=id), WriteHitIOs/WriteIOs*100)
		self.cache['lun'] = new


	def saveCache(self):
		json.dump(self.cache, open(self.cacheFile, 'w') )

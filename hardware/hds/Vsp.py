#!/usr/bin/env python 
#coding=utf-8

import pywbem,getopt, sys, datetime, time, calendar, json,os,math
import threading
from time import ctime,sleep



class Vsp:
	"""docstring for Vsp"""
	conn = None
	namespace = 'root/hitachi/smis'
	zabbix_sender = '/usr/local/zabbix_proxy/bin/zabbix_sender'
	port = 10051
	cache = {}
	cacheFile = None
	content = ''


	def __init__(self, ip,user,pwd,host,port,proxy,fun,smis_port):
		self.ip = ip
		self.user = user
		self.pwd = pwd
		self.host = host
		self.proxy = proxy
		self.port = port
		self.fun = fun
		if smis_port:
			self.smis_port = smis_port
		else
			self.smis_port = 5989

		self.conn = self.connect()

		self.lunDict = None
		self.hostDict = None
		self.hostGroupDict = None
		self.fcDict = None
		self.diskDict = None
		self.hostGroupWithPortRelation = None
		self.hostGroupWithLunRelation = None
		self.hostGroupWithHostRelation = None





		self.cacheFile = '/tmp/hds/hds' + self.ip
		if os.path.exists(self.cacheFile):
			self.cache = json.load( open(self.cacheFile, 'r') )
		else:
			f = open(self.cacheFile,'w')
			f.write('{}')
			f.close()

		item = 'self.' + fun
		eval(item)()


		self.send_to_zabbix()
		print "采集完成"


	def msg(self):
		arr1 = ['getLunDict','getHostDict','getHostGroupDict','getFcDict','getDiskDict','getHostGroupWithPortRelation','getHostGroupWithLunRelation','getHostGroupWithHostRelation','poolMsg','raidMsg','sysinfoMsg']
		threads = []



		for i in arr1:
			print "添加线程： %s" % (i)
			fun = 'self.' + i
			t = threading.Thread(target=eval(fun))
			threads.append(t)

		for t in threads:
			t.setDaemon(True)
			t.start()
			sleep(0.1)

		for i in threads:
			i.join() 



		#========== 获取所有信息 start ==================
		"""
		self.lunDict = self.getLunDict()
		self.hostDict = self.getHostDict()
		self.hostGroupDict = self.getHostGroupDict()
		self.fcDict = self.getFcDict()

		self.hostGroupWithPortRelation = self.getHostGroupWithPortRelation()#主机组和端口关系
		self.hostGroupWithLunRelation = self.getHostGroupWithLunRelation()#主机组和LUN关系
		self.hostGroupWithHostRelation = self.getHostGroupWithHostRelation()#主机组和主机关系
		"""
		#===========获取所有信息 end  ==================

		arr2 = ['lunMsg','fcportMsg','hostMsg','hostGroupMsg','hostGroupLunMsg','diskMsg','hsotGroupFcportMsg','hostWithHostGroupMsg','BatteryMsg']

		t2 = []

		for i in arr2:
			fun = 'self.' + i
			t = threading.Thread(target=eval(fun))
			t2.append(t)

		for t in t2:
			t.setDaemon(True)
			t.start()

		for i in t2:
			i.join()

		"""
		self.poolMsg()
		self.raidMsg()
		self.lunMsg()
		self.diskMsg()
		self.fcportMsg()
		self.hostMsg()
		self.hostGroupMsg()
		self.hostGroupLunMsg()
		self.hsotGroupFcportMsg()
		self.hostWithHostGroupMsg()
		"""

	def performance(self):
		self.fcSpeedPerf()
		self.lunPerf()
		self.saveCache()

	def composeContent(self,key,value):
		self.content += self.host + "\t" + '"'+ str(key) + '"' + "\t" + str(value) + "\n"


	def connect(self):
		 return pywbem.WBEMConnection('https://'+self.ip+':'+self.smis_port, (self.user, self.pwd), Vsp.namespace,None,None,None,True)


	def send_to_zabbix(self):
		tempFile = '/tmp/' + self.ip + self.fun
		f = open(tempFile,'w')
		f.write(self.content)
		f.close()
		command = '{zabbix_sender} -z {proxy} -i {file}'.format(zabbix_sender=Vsp.zabbix_sender,proxy=self.proxy,file=tempFile)
		os.popen(command)
		os.remove(tempFile)



	def poolMsg(self):
		print "采集POOL信息"
		data = self.conn.EnumerateInstances('HITACHI_ThinProvisioningPool')
		for x in data:
			if len(x):
				id = x['ElementName']
				self.composeContent('pool.name[{id}]'.format(id=id), x['ElementName']) #
				self.composeContent('pool.status[{id}]'.format(id=id), x['HealthState']) #
				self.composeContent('pool.consist[{id}]'.format(id=id), x['ConsistsOf']) #
				self.composeContent('pool.usage[{id}]'.format(id=id), x['Usage']) #
				self.composeContent('pool.capacity.size.reserved[{id}]'.format(id=id), x['ReservedSpace']) #
				self.composeContent('pool.capacity.size.free[{id}]'.format(id=id), x['RemainingManagedSpace']) # 
				self.composeContent('pool.capacity.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) #

	def raidMsg(self):
		print "采集RAID信息"
		data = self.conn.EnumerateInstances('HITACHI_StoragePool')
		for x in data:
			if len(x):
				arr = x['ElementName'].split('.')
				id =  'raid_' +  arr[-1]
				self.composeContent('raid.size.free[{id}]'.format(id=id), x['RemainingManagedSpace']) 
				self.composeContent('raid.desc[{id}]'.format(id=id), x['ElementName'])
				self.composeContent('raid.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) 
				self.composeContent('raid.status[{id}]'.format(id=id), x['HealthState']) 

		data = self.conn.EnumerateInstances('HITACHI_ArrayGroup')
		for x in data:
			if len(x):
				id = '-' .join ( x['DeviceID'].split('.') )
				id = 'raid_' + id
				self.composeContent('raid.block.size[{id}]'.format(id=id), x['BlockSize']) 
				self.composeContent('raid.number.blocks[{id}]'.format(id=id), x['NumberOfBlocks']) 
				self.composeContent('raid.level[{id}]'.format(id=id), x['ErrorMethodology']) 

	def lunMsg(self):
		print "采集LUN信息"
		#data = self.conn.EnumerateInstances('HITACHI_StorageVolume')
		data = self.lunDict
		for d in data:
			x = data[d]
			if len(x):
				tmp = x['Description'].split('.')
				id = tmp[-1]
				#id = 'lun_' + x['DeviceID']
				self.composeContent('lun.id[{id}]'.format(id=id), x['DeviceID']) 
				self.composeContent('lun.raid.level[{id}]'.format(id=id), x['ErrorMethodology']) 
				self.composeContent('lun.local[{id}]'.format(id=id), x['Caption']) 
				self.composeContent('lun.name[{id}]'.format(id=id), x['ElementName'])
				self.composeContent('lun.desc[{id}]'.format(id=id), x['Description'])
				self.composeContent('lun.size.total[{id}]'.format(id=id), x['NumberOfBlocks'] * x['BlockSize']) 
				self.composeContent('lun.status[{id}]'.format(id=id), x['HealthState']) 

	def diskMsg(self):
		print "采集DISK信息"
		#data = self.conn.EnumerateInstances('HITACHI_DiskDrive')
		data = self.diskDict

		for d in data:
			x = data[d]
			if len(x):
				#id = 'disk_' + x['DeviceID']
				id = x['Location']
				usage = 'spare'
				if 0 == x['DeviceID'].find('-'):
					usage = 'data'
				self.composeContent('disk.local[{id}]'.format(id=id), x['Location'])
				#self.composeContent('disk.function[{id}]'.format(id=id), usage)
				self.composeContent('disk.size.total[{id}]'.format(id=id), x['MaxMediaSize'])
				self.composeContent('disk.desc[{id}]'.format(id=id), ',' . join( x['CapabilityDescriptions']))
				self.composeContent('disk.status[{id}]'.format(id=id), x['HealthState'])
				self.composeContent('disk.type[{id}]'.format(id=id), x['DiskType'])
				if x.__contains__('RPM'):
					self.composeContent('disk.speed[{id}]'.format(id=id), x['RPM'])

		data =  self.conn.EnumerateInstances('HITACHI_DiskDriveView')
		for x in data:
			if len(x):
				tmpId = x['SEDeviceID']
				local = self.diskDict[tmpId]
				id = local['Location']
				#self.send_to_zabbix('disk.part.number[{id}]'.format(id=id), x['PPPartNumber']) #采集结果没有
				self.composeContent('disk.mfc[{id}]'.format(id=id), x['PPManufacturer'])
				self.composeContent('disk.blocks.size[{id}]'.format(id=id), x['SEBlockSize'])
				self.composeContent('disk.blocks[{id}]'.format(id=id), x['SENumberOfBlocks'])
				self.composeContent('disk.serial[{id}]'.format(id=id), x['PPSerialNumber'])

	def fcportMsg(self):
		print "采集FC PORT信息"
		#data = self.conn.EnumerateInstances('HITACHI_FCPort')
		data = self.fcDict
		for d in data:
			x = data[d]
			if len(x):
				id = x['ElementName']
				self.composeContent('fcif.port.number[{id}]'.format(id=id), x['PortNumber'])
				self.composeContent('fcif.speed[{id}]'.format(id=id), x['Speed'])
				self.composeContent('fcif.wwpn[{id}]'.format(id=id), x['PermanentAddress'])
				self.composeContent('fcif.type[{id}]'.format(id=id), x['PortType'])
				self.composeContent('fcif.name[{id}]'.format(id=id), x['ElementName'])
				self.composeContent('fcif.status[{id}]'.format(id=id), x['HealthState'])

	def hostGroupMsg(self):
		#data = self.conn.EnumerateInstances('HITACHI_SCSIProtocolController')
		data = self.hostGroupDict
		for d in data:
			x = data[d]
			if len(x):
				#id = 'host_group_' + x['DeviceID']
				id = x['ElementName']
				self.composeContent('storagehg.type[{id}]'.format(id=id), x['HostMode'])
				self.composeContent('storagehg.name[{id}]'.format(id=id), x['ElementName'])


	def hostMsg(self):
		print "采集HOST信息"
		#data = self.conn.EnumerateInstances('HITACHI_StorageHardwareID')
		data = self.hostDict

		for d in data:
			x = data[d]
			id = x['StorageID']
			#self.composeContent('storagehost.id[{id}]'.format(id=id), x['InstanceID'])
			self.composeContent('storagehost.port.wwn[{id}]'.format(id=id), x['StorageID'])


	def sysinfoMsg(self):
		data = self.conn.EnumerateInstances('HITACHI_StoragePoolPrimordial')
		if data:
			self.composeContent('dev.storage.size.total', data[0]['TotalManagedSpace'])
			self.composeContent('dev.storage.size.free', data[0]['RemainingManagedSpace'])
		data = self.conn.EnumerateInstances('HITACHI_StorageProduct')
		if data:
			self.composeContent('dev.serial', data[0]['IdentifyingNumber'])
			self.composeContent('dev.product.version', data[0]['Version'])
			self.composeContent('dev.mfc', data[0]['Vendor'])


	def BatteryMsg(self):
		data = self.conn.EnumerateInstances('HITACHI_Battery')
		for x in data:
			id = x['DeviceID']
			self.composeContent('battery.name[{id}]'.format(id=id), x['Name'])
			self.composeContent('battery.status[{id}]'.format(id=id), x['HealthState']) # 状态 5 是OK 



	"""
	补充主机组的下的所有LUN名称
	补充LUN下的所有主机组
	"""
	def hostGroupLunMsg(self):
		relation = self.hostGroupWithLunRelation
		lunDict = self.lunDict
		hostGroupDict = self.hostGroupDict
		#补充主机组的下的所有LUN名称
		if relation['hg']:
			hg = relation['hg']
			for x in hg:
				tmp = hostGroupDict[x]
				k = tmp['ElementName']
				print k
				lunNames = self.getAllLunsNameByLunId(hg[x],lunDict)
				self.composeContent('storagehg.mapped.luns[{id}]'.format(id=k),lunNames)
		#补充LUN下的所有主机组
		if relation['lun']:
			lun = relation['lun']
			for x in lun:
				tmp = lunDict[x]
				k = tmp['Description'].split('.')[-1]
				hostNames = self.getAllHostGroupNameByHostGroupId(lun[x],hostGroupDict)
				self.composeContent('lun.mapped.hostgroups[{id}]'.format(id=k),hostNames)

	"""
	补充主机组的 fc端口信息
	补充FC端口的  主机组信息
	"""
	def hsotGroupFcportMsg(self):
		relation = self.hostGroupWithPortRelation
		hostGroupDict = self.hostGroupDict
		fcDict = self.fcDict
		#补充主机组的 fc端口信息
		if relation['hg']:
			hg = relation['hg']
			for x in hg:
				tmp = hostGroupDict[x]
				k = tmp['ElementName']
				names = []
				wwns = []
				for i in hg[x]:
					wwns.append(fcDict[i]['DeviceID'])
					names.append(fcDict[i]['ElementName'])
				self.composeContent('storagehg.mapped.ports.wwpns[{id}]'.format(id=k),json.dumps(wwns))
				self.composeContent('storagehg.mapped.ports[{id}]'.format(id=k),json.dumps(names))

		#补充FC端口的  主机组信息
		if relation['port']:
			port = relation['port']
			for x in port:
				names = []
				tmp = fcDict[x]
				k = tmp['ElementName']
				for i in port[x]:
					names.append(hostGroupDict[i]['ElementName'])
				self.composeContent('fcif.mapped.hostgroups[{id}]'.format(id=k),json.dumps(names))

	"""
	补充主机的 主机组信息
	补充主机组的  主机信息
	"""
	def hostWithHostGroupMsg(self):
		relation = self.hostGroupWithHostRelation
		hgDict = self.hostGroupDict
		portDict = self.fcDict
		#补充主机的 主机组信息
		if relation['host']:
			host = relation['host']
			for x in host:
				names  = []#主机组的名称
				# fc 信息
				portNames = []#主机连接本存储的端口
				portWWNs = []#主机连接本存储的wwn
				# lun 信息
				lunNames = [] #lun 名称

				#关系全部要从主机组找
				for i in host[x]:
					names.append(hgDict[i]['ElementName'])

					portIDs = self.hostGroupWithPortRelation['hg'][i]
					for p in portIDs:
						fc = portDict[p]
						portNames.append(fc['ElementName'])
						portWWNs.append(fc['DeviceID'])

					lunIDs = self.hostGroupWithLunRelation['hg'][i]
					for l in lunIDs:
						lunNames.append(self.lunDict[l]['ElementName'])
				self.composeContent('storagehost.hostgroup.name[{id}]'.format(id=x),json.dumps(names))
				self.composeContent('storagehost.mapped.ports[{id}]'.format(id=x), json.dumps(portNames)) 
				self.composeContent('storagehost.mapped.ports.wwpns[{id}]'.format(id=x), json.dumps(portWWNs))
				self.composeContent('storagehost.mapped.luns[{id}]'.format(id=x), json.dumps(lunNames))

		#补充主机组的  主机信息
		""" 删除了
		hostDict = self.hostDict
		if relation['hg']:
			hg = relation['hg']
			for x in hg:
				names  = []
				for i in hg[x]:
					k = 'host_group_' + x
					names.append(hostDict[i]['ElementName'].split(' ')[-1])
				self.composeContent('host.group.hosts[{id}]'.format(id=k),json.dumps(names))
		"""


	#====================丢弃的东西 start ==============
	# 根据主机ID 返回主机组信息
	'''
	relation		主机和主机组的关系
	hostGroupDict	处理后的主机组信息
	hostId      主机ID 
	'''
	def hostWithGroup(self,relation,hostGroupDict,hostId):
		hg = None
		gid = None
		if len(hostId) and len(relation):
			for r in relation:
				if hostId == r['Privilege']['InstanceID']:
					gid = r['TargetElement']['DeviceID']
					break
		if len(gid) and gid in hostGroupDict:
			hg = hostGroupDict[gid]
		return hg

	"""
		根据主机ID和主机组ID,返回端口信息
		hgRelationPortDict	主机组和端口关系
		fcport 				端口
		groupId 			主机组ID
		hostId 				主机ID
	"""
	def hostWithFcport(self,hgRelationPortDict,fcDict,groupId):
		fc = None #[] 一个主机组应该只对应一个端口
		if len(hgRelationPortDict) and len(fcDict) and len(groupId):
			for x in hgRelationPortDict:
				if groupId == x:
					id = hgRelationPortDict[x]  #与组对应的端口信息ID
					fc = fcDict[id]
		return fc
		#====================丢弃的东西 end ==============



	"""返回lun 名称json 
	"""
	def getAllLunsNameByLunId(self,lunIDs,lunDict):
		names = []
		if lunDict and lunIDs:
			for x in lunIDs:
				name = lunDict[x]['ElementName'].split('.')[-1]
				names.append(name)
		return json.dumps(names)

	"""返回 hostgroup名称json 
	"""
	def getAllHostGroupNameByHostGroupId(self,hgIDs,hostGroupDict):
		names = []
		if hgIDs and hostGroupDict:
			for x in hgIDs:
				names.append(hostGroupDict[x]['ElementName'])
		return json.dumps(names)


	#============================返回字典 start =========================

	#把LUN信息组装成字典 [id]=[LUN]
	def getLunDict(self):
		data = self.conn.EnumerateInstances('HITACHI_StorageVolume')
		lunDict = {}
		if len(data):
			for x in data:
				id = x['DeviceID']
				lunDict[id] = x
		self.lunDict = lunDict

	#把FC 端口信息组装成字典 [id]=[fc]
	def getFcDict(self):
		data = self.conn.EnumerateInstances('HITACHI_FCPort')
		fcDict = {}
		if len(data):
			for x in data:
				id = x['DeviceID']
				fcDict[id] = x
		self.fcDict = fcDict

	#把disk 端口信息组装成字典 [id]=[disk]
	def getDiskDict(self):
		data = self.conn.EnumerateInstances('HITACHI_DiskDrive')
		tmp = {}
		if len(data):
			for x in data:
				id = x['DeviceID']
				tmp[id] = x
		self.diskDict = tmp

	#把host信息组装成字典 [id]=[host]
	def getHostDict(self):
		data = self.conn.EnumerateInstances('HITACHI_StorageHardwareID')
		hostDict = {}
		if len(data):
			for x in data:
				id = x['StorageID']
				hostDict[id] = x
		self.hostDict = hostDict

	#把主机组数据组装成 [主机组id] = [主机组信息] 的字典
	def getHostGroupDict(self):
		tmp = []
		hostGroup = self.conn.EnumerateInstances('HITACHI_SCSIProtocolController')
		hdist = {}
		for x in hostGroup:
			id = x['DeviceID']
			if (x['ElementName'] not in tmp):
				hdist[id] = x
				tmp.append(id)
		self.hostGroupDict = hdist

	#=================返回字典 end =================================

	#****************************************************************
	#****************************************************************
	#****************************************************************

	#=================返回关系 start ===============================

	"""
	返回主机组的端口的关系 hg = [端口ID]  多对一
	返回端口的主机组的关系 port = [hg]  一对多
	"""
	def getHostGroupWithPortRelation(self):
		hg = {}
		port = {}
		data = self.conn.EnumerateInstances('HITACHI_SCSIPCForFCPort')
		if data:
			for x in data:
				portID = str( x['Dependent']['DeviceID'] )
				hgID = str( x['Antecedent']['DeviceID'] )
				if not  hg.has_key(hgID):
					hg[hgID] = []
				hg[hgID].append(portID)

				if not port.has_key(portID):
					port[portID ] = []
				port[portID ].append(hgID)

		self.hostGroupWithPortRelation = {'hg':hg,'port':port}

	""" 主机组和主机的关系
	主机组 hg = [host]
	主机  host = [hg]
	"""
	def getHostGroupWithHostRelation(self):
		hg = {}
		host = {}
		data = self.conn.EnumerateInstances('HITACHI_AuthorizedTarget')
		if data:
			for x in data:
				hostID = str( x['Privilege']['InstanceID'].split('.')[-1] )
				hgID = str( x['TargetElement']['DeviceID'] )
				if not  hg.has_key(hgID):
					hg[hgID] = []
				hg[hgID].append(hostID)

				if not host.has_key(hostID):
					host[hostID ] = []
				host[hostID ].append(hgID)

		self.hostGroupWithHostRelation = {'hg':hg,'host':host}


	"""
	主机组和LUN的关系，多对多关系
	组装成两个数组 hg = [所有LUN ID]  lun = [所有hostgroup ID]
	"""
	def getHostGroupWithLunRelation(self):
		hg = {}
		lun = {}
		data = self.conn.EnumerateInstances('HITACHI_SCSIPCForStorageVolume')
		if data:
			for x in data:
				hgID = str( x['Antecedent']['DeviceID'] )
				lunID = str( x['Dependent']['DeviceID'] )
				if not  hg.has_key(hgID):
					hg[hgID] = []
				hg[hgID].append(lunID)

				if not lun.has_key(hgID):
					lun[lunID ] = []
				lun[lunID].append(hgID)

		self.hostGroupWithLunRelation = {'hg':hg,'lun':lun}


	# 主机组和FC端口的关系  [主机组ID] = [端口ID]
	def getHgRelationPortDict(self):
		hgRelationPortDict = {}
		relation = self.conn.EnumerateInstances('HITACHI_SCSIPCForFCPort')
		for x in relation:
			if len(x):
				id = x['Antecedent']['DeviceID']  #主机组
				hgRelationPortDict[id] = x['Dependent']['DeviceID']  # 端口
		return hgRelationPortDict


	#=================返回关系 end =================================



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
		self.getFcDict()
		new = {}
		if len(data):
			timestamp = calendar.timegm(data[0]['StatisticTime'].datetime.timetuple())
			for x in data:
				d = x['InstanceID'].split('.')
				item = d[-1]
				arr = self.fcDict[item]
				id = arr['ElementName']
				tmp = {}
				tmp['timestamp'] = timestamp
				tmp['KBytesTransferred'] = x['KBytesTransferred'] #总流量
				tmp['TotalIOs'] = x['TotalIOs'] #总IO/S
				new[id] = tmp
				#计算
				if old and old.__contains__(id) and timestamp-old[id]['timestamp'] > 0:
					KBytesTransferred = ( x['KBytesTransferred'] - old[id]['KBytesTransferred'] ) / (timestamp-old[id]['timestamp'])
					#发送到ZABBIX
					self.composeContent('fcif.inout[{id}]'.format(id=id), KBytesTransferred )
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
		self.getLunDict()
		new = {}
		if len(data):
			timestamp = calendar.timegm(data[0]['StatisticTime'].datetime.timetuple())
			for x in data:
				tid = x['InstanceID'].split('.')[-1]
				arr = self.lunDict[tid]
				id = arr['Description'].split('.')[-1]
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
					self.composeContent('lun.rw.rate[{id}]'.format(id=id), KBytesTransferred )
					self.composeContent('lun.rw.io.rate[{id}]'.format(id=id), TotalIOs )
					self.composeContent('lun.read.io.rate[{id}]'.format(id=id), ReadIOs )
					self.composeContent('lun.write.io.rate[{id}]'.format(id=id), WriteIOs )
					#缓存命中率
					if ReadIOs > 0:
						self.composeContent('lun.read.io.hit[{id}]'.format(id=id), ReadHitIOs/ReadIOs*100)
					if WriteIOs > 0:
						self.composeContent('lun.write.io.hit[{id}]'.format(id=id), WriteHitIOs/WriteIOs*100)
		self.cache['lun'] = new


	def saveCache(self):
		json.dump(self.cache, open(self.cacheFile, 'w') )

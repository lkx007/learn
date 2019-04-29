#!/usr/bin/env python 
#coding=utf-8

import pywbem,getopt, sys, datetime, time, calendar, json,os,math,gc
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
		else:
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


		if not os.path.exists('/tmp/hds/'):
			os.makedirs('/tmp/hds/',0777);


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
		arr1 = ['getLunDict','getHostDict','getHostGroupDict','getFcDict','getDiskDict','poolMsg','raidMsg','sysinfoMsg']
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



		arr2 = ['lunMsg','fcportMsg','hostMsg','hostGroupMsg','hostGroupLunMsg','LunHostGroupMsg','diskMsg','hsotGroupFcportMsg','FcportHsotGroupMsg','hostWithHostGroupMsg','hostWithLunMsg','hostWithFcMsg','BatteryMsg']

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


	def performance(self):
		self.fcSpeedPerf()
		self.lunPerf()
		self.saveCache()

	def composeContent(self,key,value):
		self.content += self.host + "\t" + '"'+ str(key) + '"' + "\t" + str(value) + "\n"


	def connect(self):
		 return pywbem.WBEMConnection('https://' + self.ip + ':' + str(self.smis_port), (self.user, self.pwd), Vsp.namespace,None,None,None,True)


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
		del data
		gc.collect()

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
		del data
		gc.collect()

		data = self.conn.EnumerateInstances('HITACHI_ArrayGroup')
		for x in data:
			if len(x):
				id = '-' .join ( x['DeviceID'].split('.') )
				id = 'raid_' + id
				self.composeContent('raid.blocks.size[{id}]'.format(id=id), x['BlockSize']) 
				self.composeContent('raid.blocks.number[{id}]'.format(id=id), x['NumberOfBlocks']) 
				self.composeContent('raid.level[{id}]'.format(id=id), x['ErrorMethodology']) 
		del data
		gc.collect()
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
				#self.composeContent('lun.local[{id}]'.format(id=id), x['Caption'])#不要了 
				self.composeContent('lun.name[{id}]'.format(id=id), x['ElementName'])
				self.composeContent('lun.desc[{id}]'.format(id=id), x['Description'])
				self.composeContent('lun.size.total[{id}]'.format(id=id), x['NumberOfBlocks'] * x['BlockSize']) 
				self.composeContent('lun.status[{id}]'.format(id=id), x['HealthState']) 
		del data
		gc.collect()

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
		del data
		gc.collect()

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
		del data
		gc.collect()

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
		del data
		gc.collect()

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
		del data
		gc.collect()

	def hostMsg(self):
		print "采集HOST信息"
		#data = self.conn.EnumerateInstances('HITACHI_StorageHardwareID')
		data = self.hostDict
		for d in data:
			x = data[d]
			id = x['StorageID']
			#self.composeContent('storagehost.id[{id}]'.format(id=id), x['InstanceID'])
			self.composeContent('storagehost.port.wwn[{id}]'.format(id=id), x['StorageID'])
		del data
		gc.collect()

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
		del data
		gc.collect()

	def BatteryMsg(self):
		data = self.conn.EnumerateInstances('HITACHI_Battery')
		for x in data:
			id = x['DeviceID']
			self.composeContent('battery.name[{id}]'.format(id=id), x['Name'])
			self.composeContent('battery.status[{id}]'.format(id=id), x['HealthState']) # 状态 5 是OK 
		del data
		gc.collect()



	#补充主机组的下的所有LUN名称
	def hostGroupLunMsg(self):
		print "采集主机组下的LUN信息"
		hostGroupDict = self.hostGroupDict
		source = self.conn.EnumerateInstanceNames('HITACHI_SCSIProtocolController')
		for s in source:
			k=s['DeviceID']
			name = hostGroupDict[k]['ElementName']
			cs_inst = self.conn.GetInstance(s)
			dmsg = self.conn.Associators(cs_inst.path,'HITACHI_SCSIPCForStorageVolume','HITACHI_StorageVolume')
			tmp = set()

			for x in dmsg:
				tmp.add(x['ElementName'])
			self.composeContent('storagehg.mapped.luns[{id}]'.format(id=name),json.dumps(list(tmp)))


	#补充LUN下的所有主机组
	def LunHostGroupMsg(self):
		print "采集LUN下的主机组信息"
		lunDict = self.lunDict
		source = self.conn.EnumerateInstanceNames('HITACHI_StorageVolume')
		for s in source:
			k=s['DeviceID']
			name = lunDict[k]['ElementName']
			cs_inst = self.conn.GetInstance(s)
			dmsg = self.conn.Associators(cs_inst.path,'HITACHI_SCSIPCForStorageVolume','HITACHI_SCSIProtocolController')
			tmp = set()
			for x in dmsg:
				tmp.add(x['ElementName'])
			self.composeContent('lun.mapped.hostgroups[{id}]'.format(id=name),json.dumps(list(tmp)))


	#补充主机组的 fc端口信息
	def hsotGroupFcportMsg(self):
		print "采集主机组的光纤端口信息"
		hostGroupDict = self.hostGroupDict
		source = self.conn.EnumerateInstanceNames('HITACHI_SCSIProtocolController')
		for s in source:
			k=s['DeviceID']
			name = hostGroupDict[k]['ElementName']
			cs_inst = self.conn.GetInstance(s)
			dmsg = self.conn.Associators(cs_inst.path,'HITACHI_SCSIPCForFCPort','HITACHI_FCPort')
			wwns = set()
			names = set()
			for x in dmsg:
				wwns.add(x['DeviceID'])
				names.add(x['ElementName'])
			self.composeContent('storagehg.mapped.ports.wwpns[{id}]'.format(id=name),json.dumps(list(wwns)))
			self.composeContent('storagehg.mapped.ports[{id}]'.format(id=name),json.dumps(list(names)))

	#补充FC端口的  主机组信息
	def FcportHsotGroupMsg(self):
		print "采集光纤端口的主机组信息"
		fcDict = self.fcDict
		source = self.conn.EnumerateInstanceNames('HITACHI_FCPort')
		for s in source:
			k=s['DeviceID']
			name = fcDict[k]['ElementName']
			cs_inst = self.conn.GetInstance(s)
			dmsg = self.conn.Associators(cs_inst.path,'HITACHI_SCSIPCForFCPort','HITACHI_SCSIProtocolController')
			names = set()
			for x in dmsg:
				names.add(x['ElementName'])
			self.composeContent('fcif.mapped.hostgroups[{id}]'.format(id=name),json.dumps(list(names)))

	#主机与主机组的信息
	def hostWithHostGroupMsg(self):
		print "采集主机属于那些主机组信息"
		hostDict = self.hostDict
		source = self.conn.EnumerateInstanceNames('HITACHI_StorageHardwareID')
		for s in source:
			k= s['InstanceID'].split(".")[-1]
			name = hostDict[k]['ElementName']
			cs_inst = self.conn.GetInstance(s)
			#主机 属于主机组
			t1 = self.conn.AssociatorNames(cs_inst.path,'HITACHI_AuthorizedSubject','HITACHI_AuthorizedPrivilege')
			if len(t1)>0:
				t2 = self.conn.Associators(t1[0],'HITACHI_AuthorizedTarget','HITACHI_SCSIProtocolController')
				tmp = set()
				#可能会以属于多个组
				for x in t2:
					tmp.add(x['ElementName'])
				self.composeContent('storagehost.hostgroup.name[{id}]'.format(id=name),json.dumps(list(tmp)))

	#主机与Lun的信息
	def hostWithLunMsg(self):
		print "采集主机下所有LUN信息"
		hostDict = self.hostDict
		source = self.conn.EnumerateInstanceNames('HITACHI_StorageHardwareID')
		for s in source:
			k= s['InstanceID'].split(".")[-1]
			name = hostDict[k]['ElementName']
			cs_inst = self.conn.GetInstance(s)
			#主机 下所有LUN
			tmp = set()
			t1 = self.conn.AssociatorNames(cs_inst.path,'HITACHI_AuthorizedSubject','HITACHI_AuthorizedPrivilege')
			for t11 in t1:
				t2 = self.conn.AssociatorNames(t11,'HITACHI_AuthorizedTarget','HITACHI_SCSIProtocolController')
				#可能会以属于多个组
				for t22 in t2:
					t3 = self.conn.Associators(t22,'HITACHI_SCSIPCForStorageVolume','HITACHI_StorageVolume')
					if t3:
						tmp.add(t3['ElementName'])
			self.composeContent('storagehost.mapped.luns[{id}]'.format(id=name),json.dumps(list(tmp)))


	#主机与FC端口的信息
	def hostWithFcMsg(self):
		print "采集主机下所有的光纤端口信息"
		hostDict = self.hostDict
		source = self.conn.EnumerateInstanceNames('HITACHI_StorageHardwareID')
		for s in source:
			k= s['InstanceID'].split(".")[-1]
			name = hostDict[k]['ElementName']
			cs_inst = self.conn.GetInstance(s)
			#主机 下所有 FC 端口
			ports = set()
			wwpns = set()
			t1 = self.conn.AssociatorNames(cs_inst.path,'HITACHI_AuthorizedSubject','HITACHI_AuthorizedPrivilege')
			for t11 in t1:
				t2 = self.conn.AssociatorNames(t11,'HITACHI_AuthorizedTarget','HITACHI_SCSIProtocolController')
				#可能会以属于多个组
				for t22 in t2:
					t3 = self.conn.AssociatorNames(t22,'HITACHI_SCSIProtocolEndpointAvailableForProtocolController','HITACHI_SCSIProtocolEndpoint')
					for t33  in t3:
						t4 = self.conn.Associators(t22,'HITACHI_FCPortForSCSIProtocolEndpointImplementation','HITACHI_FCPort')
						if t4:
							ports.add(t4['ElementName'])
							wwpns.add(t4['DeviceID'])
			self.composeContent('storagehost.mapped.ports[{id}]'.format(id=name),json.dumps(list(ports)))
			self.composeContent('storagehost.mapped.ports.wwpns[{id}]'.format(id=name),json.dumps(list(wwpns)))


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
		del data
		gc.collect()
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
		del data
		gc.collect()

	def saveCache(self):
		json.dump(self.cache, open(self.cacheFile, 'w') )

"""
if __name__ == '__main__':
	cluster='10.244.48.18'
	user='maintenance'
	password='GZ@cloud2018!'
	port='10050'
	proxy='10.236.9.57'
	fun='msg'
	smis_port='5989'
	hostname='GZ-XXY-A4_101-E04-03U_35U-HIT-HDS_VSP_G400-B01'
	Vsp(cluster,user,password,hostname,port,proxy,fun,smis_port)
"""
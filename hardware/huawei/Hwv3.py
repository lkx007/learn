#!/usr/bin/env python 
#coding=utf-8

import pywbem,getopt, sys, datetime, time, calendar, json,os,math,re
import threading
from time import ctime,sleep



class Hwv3:
	"""docstring for Hwv3
		自己配置的都是5989
		存储用系统号区分，每一个指标都带有序列号，格式：序列号_指标
		6800v3 没有IO数据，只有状态，关键告警还要snmptrap
	"""
	conn = None
	namespace = 'root/huawei'
	zabbix_sender = '/usr/local/zabbix_proxy/bin/zabbix_sender'
	port = 10051 # zabbix 端口
	cache = {}
	cacheFile = None
	content = ''

	def __init__(self, ip,user,pwd,host,port,proxy,fun,serial):
		self.ip = ip
		self.user = user
		self.pwd = pwd
		self.host = host
		self.proxy = proxy
		self.port = port
		self.fun = fun
		self.serial = serial

		self.conn = self.connect()


		self.cacheFile = '/tmp/huawei/hw' + self.ip
		if os.path.exists(self.cacheFile):
			self.cache = json.load( open(self.cacheFile, 'r') )
		else:
			f = open(self.cacheFile,'w')
			f.write('{}')
			f.close()

		self.lunInstance()

		item = 'self.' + fun
		eval(item)()
		self.send_to_zabbix()
		print "采集完成"


	def msg(self):
		arr2 = ['fcportMsg','poolMsg','enclosureMsg','raidMsg','poolInRaid','diskMsg','diskOtherMsg','diskSizeMsg','hostMsg','hostGroupMsg','LunMsg','lunWithHost','lunInGroup','lunInPool','LunGroupMsg','baseMsg','baseSizeMsg','baseOtherMsg']
		#arr2 = ['hostMsg']
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
		arr = ['fcportMsg','poolMsg','enclosureMsg','raidMsg','diskMsg','LunMsg']
		t2 = []
		for i in arr:
			fun = 'self.' + i
			t = threading.Thread(target=eval(fun))
			t2.append(t)
		for t in t2:
			t.setDaemon(True)
			t.start()
		for i in t2:
			i.join()

	def composeContent(self,key,value):
		value = str(value)
		if len(value) == 0:
			value = '--'
		self.content += self.host + "\t" + str(key) + "\t" + str(value) + "\n"


	def connect(self):
		 return pywbem.WBEMConnection('https://'+self.ip, (self.user, self.pwd), Hwv3.namespace,None,None,None,True)

	def saveCache(self):
		json.dumps(self.cache, open(self.cacheFile, 'w') )

	def send_to_zabbix(self):
		tempFile = '/tmp/' + self.ip + self.fun
		f = open(tempFile,'w')
		f.write(self.content)
		f.close()
		command = '{zabbix_sender} -z {proxy} -i {file}'.format(zabbix_sender=Hwv3.zabbix_sender,proxy=self.proxy,file=tempFile)
		os.popen(command)
		os.remove(tempFile)




	def fcportMsg(self):
		print "采集FC PORT信息"
		data = self.conn.EnumerateInstances('HuaSy_FrontEndFCPort')
		for x in data:
			if x['DeviceID'].startswith(self.serial):
				id = x['DeviceID']
				if self.fun == 'msg':
					self.composeContent('fcif.speed[{id}]'.format(id=id), x['Speed'])
					self.composeContent('fcif.wwpn[{id}]'.format(id=id), x['PermanentAddress'])
					self.composeContent('fcif.name[{id}]'.format(id=id), x['ElementName'])
					#self.composeContent('fcif.type[{id}]'.format(id=id), x['PortType'])
					#self.composeContent('fcif.max.speed[{id}]'.format(id=id), x['MaxSpeed'])
				else:
					status = x['OperationalStatus']
					self.composeContent('fcif.status[{id}]'.format(id=id), status[0])

	def poolMsg(self):
		print "采集存储池信息"
		data = self.conn.EnumerateInstances('HuaSy_ConcreteStoragePool')
		for x in data:
			id = x['InstanceID']
			if id.startswith(self.serial):
				if self.fun == 'msg':
					self.composeContent('pool.name[{id}]'.format(id=id), x['ElementName'])
					self.composeContent('pool.capacity.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) #池总容量大小
					self.composeContent('pool.capacity.size.free[{id}]'.format(id=id), x['RemainingManagedSpace']) # 池剩余容量大小
					self.composeContent('pool.capacity.size.used[{id}]'.format(id=id), x['TotalManagedSpace']-x['RemainingManagedSpace']) #池已用容量大小
					#self.composeContent('pool.operational.status[{id}]'.format(id=id), x['OperationalStatus'])#运行状态
					self.composeContent('pool.id[{id}]'.format(id=id), x['PoolID'])#
				else:
					self.composeContent('pool.status[{id}]'.format(id=id), x['HealthState'])#健康状态


	# 控制框或硬盘框
	def enclosureMsg(self):
		print "采集控制框或硬盘框信息"
		data = self.conn.EnumerateInstances('HuaSy_EnclosureChassis')
		for x in data:
			id = x['Tag']
			if id.startswith(self.serial):
				if self.fun == 'msg':
					self.composeContent('enclosure.name[{id}]'.format(id=id), x['ElementName']) # 控制器名
					self.composeContent('enclosure.mfc[{id}]'.format(id=id), x['Manufacturer']) # 厂家
					self.composeContent('enclosure.model[{id}]'.format(id=id), x['Model']) # 型号
					self.composeContent('enclosure.serial[{id}]'.format(id=id), x['SerialNumber']) # 序列号
					self.composeContent('enclosure.type[{id}]'.format(id=id), x['ChassisPackageType']) # 类型 17：控制框，18：硬盘框
				else:
					self.composeContent('enclosure.status[{id}]'.format(id=id), x['HealthState']) # 健康状态

	# 阵列信息 （磁盘域信息）
	def raidMsg(self):
		print "采集阵列信息"
		data = self.conn.EnumerateInstances('HuaSy_DiskStoragePool')
		for x in data:
			id = x['InstanceID']
			if id.startswith(self.serial):
				if self.fun == 'msg':
					self.composeContent('raid.name[{id}]'.format(id=id), x['ElementName']) # 名称
					self.composeContent('raid.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) # 总容量
					self.composeContent('raid.size.used[{id}]'.format(id=id), x['RemainingManagedSpace']) #已使用容量
					self.composeContent('raid.size.free[{id}]'.format(id=id), x['TotalManagedSpace'] - x['RemainingManagedSpace'] ) #
					self.composeContent('raid.size.available[{id}]'.format(id=id), x['HuaSyAvailableCapacity']) # 未分配的空闲容量
					#self.composeContent('raid.pool.id[{id}]'.format(id=id), x['PoolID'].split('_')[-1]) # 存储ID 这是一个字符PD_0,要处理下
				else:
					self.composeContent('raid.status[{id}]'.format(id=id), x['HealthState']) # 健康状态

	# 存储池所在的磁盘域
	def poolInRaid(self):
		cs_paths = self.conn.EnumerateInstanceNames('HuaSy_ConcreteStoragePool')
		for cs_path in cs_paths:
			id  = cs_path['InstanceID'].decode()
			if id.startswith(self.serial):
				cs_inst = self.conn.GetInstance(cs_path)
				dmsg = self.conn.Associators(cs_inst.path,'HuaSy_AllocatedFromStoragePool','HuaSy_DiskStoragePool')
				if len(dmsg)>0:
					self.composeContent('pool.in.raid[{id}]'.format(id=cs_path['InstanceID']), dmsg[0]['ElementName']) # 存储池所在的磁盘域

	#硬盘信息
	"""
		HuaSy_DiskDrive 基本信息
		HuaSy_DiskExtent 容量
		HuaSy_DiskPackag 物理信息
	"""
	def diskMsg(self):
		print "采集硬盘基本信息"
		data = self.conn.EnumerateInstances('HuaSy_DiskDrive')
		for x in data:
			id = x['DeviceID']
			if id.startswith(self.serial):
				if self.fun == 'msg':
					self.composeContent('disk.name[{id}]'.format(id=id), x['ElementName']) # 名称
					self.composeContent('disk.type[{id}]'.format(id=id), x['Caption']) # 标题来当类型
					self.composeContent('disk.encryption[{id}]'.format(id=id), x['Encryption']) # 加密类型 0：未加密
				else:
					self.composeContent('disk.status[{id}]'.format(id=id), x['EnabledState']) # 状态 2：正常，其它 未知
					self.composeContent('disk.operational.status[{id}]'.format(id=id), x['OperationalStatus'][0]) # 

	def diskSizeMsg(self): 
		print "采集硬盘容量信息" 
		source = self.conn.EnumerateInstanceNames('HuaSy_DiskDrive')
		for s in source:
			id = s['DeviceID']
			if id.startswith(self.serial):
				cs_inst = self.conn.GetInstance(s)
				dmsg = self.conn.Associators(cs_inst.path,'HuaSy_MediaPresent','HuaSy_DiskExtent')
				if dmsg:
					self.composeContent('disk.blocks.number[{id}]'.format(id=id), dmsg[0]['NumberOfBlocks']) #  块数
					self.composeContent('disk.blocks.size[{id}]'.format(id=id), dmsg[0]['BlockSize']) # 块大小 4K 
					self.composeContent('disk.size.total[{id}]'.format(id=id), dmsg[0]['NumberOfBlocks'] * dmsg[0]['BlockSize']) #  容量 

	def diskOtherMsg(self):
		print "采集硬盘扩展信息"
		data = self.conn.EnumerateInstances('HuaSy_DiskPackage')
		for x in data:
			id = x['Tag']
			if id.startswith(self.serial):
				self.composeContent('disk.Version[{id}]'.format(id=id), x['Version']) #  版本
				self.composeContent('disk.serial[{id}]'.format(id=id), x['SerialNumber']) # 序列号
				self.composeContent('disk.model[{id}]'.format(id=id), x['Model']) # 型号
				self.composeContent('disk.mfc[{id}]'.format(id=id), x['Manufacturer']) #厂家 
	# 主机信息
	"""
	主机信息没有找到类，只找一个启动器，主机信息需要从启动器过去重拿出来
	启动器：主机关联端口的关联表，这里只取FC端口
	保留 InstanceID  用作关联主机类型时的过滤
	一台虚拟主机有一个或多个HBA卡

	"""
	def hostMsg(self):
		print "采集主机信息"
		data = self.conn.EnumerateInstances('HuaSy_StorageHardwareID ')
		names = []
		ids = {}
		tmp = {} #映射的远程wwpn,即启动器
		tid = ''#记录第一个主机ID
		source = self.conn.EnumerateInstanceNames('HuaSy_StorageHardwareID') #
		for x in data:
			name = x['ElementName']
			id = oid = x['InstanceID']
			id = '"' + id + '"'
			ids[id] = name
			if oid.startswith(self.serial):
				if name not in names:  # 
					names.append(name)
					self.composeContent('storagehost.name[{id}]'.format(id=id), name) #

					#操作系统,所属主机组,映射的LUN
					for s in source:
						if s['InstanceID'] == oid:
							cs_inst = self.conn.GetInstance(s)
							#操作系统
							dmsg = self.conn.Associators(cs_inst.path,'HuaSy_ElementSettingData','HuaSy_StorageClientSettingData')
							if dmsg:
								self.composeContent('storagehost.type[{id}]'.format(id=id), dmsg[0]['ElementName']) #操作系统

							#所属主机组
							dmsg = self.conn.Associators(cs_inst.path,'HuaSy_MemberOfCollection','HuaSy_InitiatorMasKingGroup')
							if dmsg:
								self.composeContent('storagehost.hostgroup.name[{id}]'.format(id=id), dmsg[0]['ElementName']) #所属主机组

							#映射的LUN
							t1 = self.conn.AssociatorNames(cs_inst.path,'HuaSy_AuthorizedSubject','HuaSy_AuthorizedPrivilege')
							if len(t1)>0:
								t2 = self.conn.AssociatorNames(t1[0],'HuaSy_AuthorizedTarget','HuaSy_MaskingSCSIProtocolController')
								if t2:
									t3 = self.conn.Associators(t2[0],'HuaSy_ProtocolControllerForUnit','HuaSy_StorageVolume')
									if t3:
										luns = set()
										for t in t3:
											luns.add(t['ElementName'])
										if luns:
											self.composeContent('storagehost.mapped.luns[{id}]'.format(id=id), json.dumps(list(luns))) #存储主机已映射卷列表

					#映射的远程wwpn,即启动器
					tid = id
					tmp[id] = []
					tmp[id].append(x['StorageID']) # wwpn
				else:
					tmp[tid].append(x['StorageID']) # wwpn
		for x in tmp:#映射的远程wwpn,即启动器（光纤端口）
			self.composeContent('storagehost.ports.wwpns[{id}]'.format(id=x), json.dumps(tmp[x])) #存储主机WWPN列表




	# 主机组信息
	def hostGroupMsg(self):
		print "采集主机组信息"
		data = self.conn.EnumerateInstances('HuaSy_InitiatorMaskingGroup')
		source = self.conn.EnumerateInstanceNames('HuaSy_InitiatorMasKingGroup')
		for x in data:
			id = x['InstanceID']
			if id.startswith(self.serial):
				name = x['ElementName']
				self.composeContent('storagehg.name[{id}]'.format(id=id), name) #  主机组名称
				#self.composeContent('storagehg.id[{id}]'.format(id=id), id) #  主机组名称
				#主机组下所有主机
				for s in source:
					if s['InstanceID'] == id:
						cs_inst = self.conn.GetInstance(s)
						dmsg = self.conn.Associators(cs_inst.path,'HuaSy_MemberOfCollection','HuaSy_StorageHardwareID')
						tmp = set()
						for d in dmsg:
							tmp.add(d['ElementName'])
						self.composeContent('storagehg.host.name[{id}]'.format(id=id), json.dumps(list(tmp))) #  主机组下所有主机


	def lunInstance(self):
		self.lunInstance = self.conn.EnumerateInstanceNames('HuaSy_StorageVolume')


	def LunMsg(self):
		print "采集LUN信息"
		data = self.conn.EnumerateInstances('HuaSy_StorageVolume')
		for x in data:
			id = x['DeviceID']
			if id.startswith(self.serial):
				if self.fun == 'msg':
					self.composeContent('lun.name[{id}]'.format(id=id), x['ElementName']) # 名称
					self.composeContent('lun.size.total[{id}]'.format(id=id), x['NumberOfBlocks'] * x['BlockSize']) #
					self.composeContent('lun.blocks.number[{id}]'.format(id=id), x['NumberOfBlocks']) #
					self.composeContent('lun.blocks.size[{id}]'.format(id=id), x['BlockSize']) #
					self.composeContent('lun.thinly.provisioned[{id}]'.format(id=id), x['ThinlyProvisioned']) # 是否是精简卷
					self.composeContent('lun.wwn[{id}]'.format(id=id), x['Name']) # lun wwn 
				else:
					self.composeContent('lun.nofailure[{id}]'.format(id=id), x['NoSinglePointOfFailure']) # 无单点故障

	# LUN 映射的主机
	def lunWithHost(self):
		print "lun 映射的主机"
		cs_paths = self.lunInstance
		for cs_path in cs_paths:
			id = cs_path['DeviceID']
			if id.startswith(self.serial):
				cs_inst = self.conn.GetInstance(cs_path)
				t1 = self.conn.AssociatorNames(cs_inst.path,'HuaSy_ProtocolControllerForUnit','HuaSy_MaskingSCSIProtocolController')
				if t1:
					t2 = self.conn.AssociatorNames(t1[0],'HuaSy_AuthorizedTarget','HuaSy_AuthorizedPrivilege') # 多个
					hosts = set()
					for o in t2:
						t3 = self.conn.Associators(o,'HuaSy_AuthorizedSubject','HuaSy_StorageHardwareID')
						hosts.add(t3[0]['ElementName'])
					self.composeContent('lun.mapped.host[{id}]'.format(id=cs_path['DeviceID']), json.dumps(list(hosts)))# LUN 映射的主机

	#lun所在lun组
	def lunInGroup(self):
		print "lun所在lun组"
		for cs_path in self.lunInstance:
			id = cs_path['DeviceID']
			if id.startswith(self.serial):
				cs_inst = self.conn.GetInstance(cs_path)
				#lun所在lun组
				dmsg = self.conn.Associators(cs_inst.path,'HuaSy_OrderedMemberOfCollection','HuaSy_DeviceMaskingGroup')
				if len(dmsg)>0:
					self.composeContent('lun.in.group[{id}]'.format(id=cs_path['DeviceID']), dmsg[0]['ElementName']) # lun 所在 lun组

	#lun所属存储池
	def lunInPool(self):
		print "lun所属存储池"
		for cs_path in self.lunInstance :
			id = cs_path['DeviceID']
			if id.startswith(self.serial):
				cs_inst = self.conn.GetInstance(cs_path)
				dmsg = self.conn.Associators(cs_inst.path,'HuaSy_AllocatedFromStoragePool','HuaSy_ConcreteStoragePool')
				if dmsg:
					self.composeContent('lun.pool.name[{id}]'.format(id=cs_path['DeviceID']), dmsg[0]['ElementName'])#lun所属存储池


	def LunGroupMsg(self):
		print "采集LUN信息"
		data = self.conn.EnumerateInstances('HuaSy_DeviceMaskingGroup')
		for x in data:
			id = x['InstanceID']
			if id.startswith(self.serial):
				self.composeContent('lg.name[{id}]'.format(id=id), x['ElementName']) # 名称



	def baseOtherMsg(self):
		data = self.conn.EnumerateInstances('HuaSy_StorageSystem')
		for x in data:
			id = x['Name'].split(':')[0]   #x['Name']
			if id.startswith(self.serial):
				if self.fun == 'msg':
					self.composeContent('dev.syslocation[{id}]'.format(id=id), x['ElementName']) # 
				else:
					self.composeContent('dev.status[{id}]'.format(id=id), x['HealthState']) # 


	def baseMsg(self):
		print "采集设备基本信息"
		data = self.conn.EnumerateInstances('HuaSy_ArrayProduct')
		for x in data:
			id = x['IdentifyingNumber'] #x['Name']
			if id.startswith(self.serial):
				self.composeContent('dev.serial[{id}]'.format(id=id), x['IdentifyingNumber']) # 
				self.composeContent('dev.name[{id}]'.format(id=id), x['ElementName']) # 
				self.composeContent('dev.version[{id}]'.format(id=id), x['Version']) # 
				self.composeContent('dev.mfc[{id}]'.format(id=id), x['Vendor']) #

	def baseSizeMsg(self):
		data = self.conn.EnumerateInstances('HuaSy_PrimordialStoragePool')
		for x in data:
			id = x['InstanceID'].split(':')[0]
			if id.startswith(self.serial):
				self.composeContent('dev.storage.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) #总容量 
				self.composeContent('dev.storage.size.free[{id}]'.format(id=id), x['RemainingManagedSpace']) # 剩余容量
				self.composeContent('dev.storage.size.used[{id}]'.format(id=id), x['TotalManagedSpace']-x['RemainingManagedSpace']) #使用容量


"""
ip = '10.142.88.7'
user = 'smis_admin'
pwd = 'Admin@12'
host = 'NM-XX-A5403-F03-01U_46U-HW-6800V3-B01'
port = 10051
proxy = '10.142.88.4'
fun = 'msg'
h = Hwv3(ip,user,pwd,host,port,proxy,fun)
"""
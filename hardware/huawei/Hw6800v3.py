#!/usr/bin/env python 
#coding=utf-8

import pywbem,getopt, sys, datetime, time, calendar, json,os,math,re
import threading
from time import ctime,sleep



class Hw6800v3:
	"""docstring for Hw6800v3
		自己配置的都是5989
		存储用系统号区分，每一个指标都带有序列号，格式：序列号_指标


	"""
	conn = None
	namespace = 'root/huawei'
	zabbix_sender = '/usr/local/zabbix_proxy/bin/zabbix_sender'
	port = 10051 # zabbix 端口
	cache = {}
	cacheFile = None
	content = ''

	def __init__(self, ip,user,pwd,host,port,proxy,fun):
		self.ip = ip
		self.user = user
		self.pwd = pwd
		self.host = host
		self.proxy = proxy
		self.port = port
		self.fun = fun

		self.conn = self.connect()


		self.cacheFile = '/tmp/huawei/hw' + self.ip
		if os.path.exists(self.cacheFile):
			self.cache = json.load( open(self.cacheFile, 'r') )
		else:
			f = open(self.cacheFile,'w')
			f.write('{}')
			f.close()

		item = 'self.' + fun
		eval(item)()


		#self.send_to_zabbix()
		print "采集完成"


	def msg(self):

		arr2 = ['fcportMsg']

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
		value = str(value)
		if len(value) == 0:
			value = '--'
		self.content += self.host + "\t" + str(key) + "\t" + str(value) + "\n"


	def connect(self):
		 return pywbem.WBEMConnection('https://'+self.ip, (self.user, self.pwd), Hw6800v3.namespace,None,None,None,True)

	def saveCache(self):
		json.dump(self.cache, open(self.cacheFile, 'w') )

	def send_to_zabbix(self):
		tempFile = '/tmp/' + self.ip + self.fun
		f = open(tempFile,'w')
		f.write(self.content)
		f.close()
		command = '{zabbix_sender} -z {proxy} -i {file}'.format(zabbix_sender=Hw6800v3.zabbix_sender,proxy=self.proxy,file=tempFile)
		os.popen(command)
		os.remove(tempFile)




	def fcportMsg(self):
		print "采集FC PORT信息"
		data = self.conn.EnumerateInstances('HuaSy_FrontEndFCPort')
		for x in data:
			if len(x):
				#id = x['InstanceID'].split(':')[0] + '_' + x['ElementName']
				id = x['InstanceID']
				status = x['OperationalStatus']
				self.composeContent('fcif.status[{id}]'.format(id=id), status[0])
				self.composeContent('fcif.speed[{id}]'.format(id=id), x['Speed'])
				self.composeContent('fcif.wwpn[{id}]'.format(id=id), x['PermanentAddress'])
				self.composeContent('fcif.name[{id}]'.format(id=id), x['ElementName'])
				#self.composeContent('fcif.type[{id}]'.format(id=id), x['PortType'])
				#self.composeContent('fcif.max.speed[{id}]'.format(id=id), x['MaxSpeed'])



	def poolMsg(self):
		print "采集存储池信息"
		data = self.conn.EnumerateInstances('HuaSy_ConcreteStoragePool')
		for x in data:
			#id = x['InstanceID'].split(':')[0] + '_' + x['ElementName']
			id = x['InstanceID']
			self.composeContent('pool.name[{id}]'.format(id=id), x['ElementName'])
			self.composeContent('pool.capacity.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) #池总容量大小
			self.composeContent('pool.capacity.size.free[{id}]'.format(id=id), x['RemainingManagedSpace']) # 池剩余容量大小
			self.composeContent('pool.capacity.size.used[{id}]'.format(id=id), x['TotalManagedSpace']-x['RemainingManagedSpace']) #池已用容量大小
			self.composeContent('pool.operational.status[{id}]'.format(id=id), x['OperationalStatus'])#运行状态
			self.composeContent('pool.status[{id}]'.format(id=id), x['HealthState'])#健康状态
			self.composeContent('pool.id[{id}]'.format(id=id), x['PoolID'])#


	# 控制框或硬盘框
	def enclosureMsg(self):
		print "采集控制框或硬盘框信息"
		data = self.conn.EnumerateInstances('HuaSy_EnclosureChassis')
		for x in data:
			#id = x['Tag'].split(':')[0] + '_' + x['ElementName']
			id = x['Tag']
			self.composeContent('enclosure.name[{id}]'.format(id=id), x['ElementName']) # 控制器名
			self.composeContent('enclosure.operational.status[{id}]'.format(id=id), x['OperationalStatus']) #  动行状态 
			self.composeContent('enclosure.status[{id}]'.format(id=id), x['HealthState']) # 健康状态
			self.composeContent('enclosure.mfc[{id}]'.format(id=id), x['Manufacturer']) # 厂家
			self.composeContent('enclosure.model[{id}]'format(id=id), x['Model ']) # 型号
			self.composeContent('enclosure.serial[{id}]'.format(id=id), x['SerialNumber']) # 序列号
			self.composeContent('enclosure.type[{id}]'.format(id=id), x['ChassisPackageType']) # 类型 17：控制框，18：硬盘框

	# 阵列信息 （磁盘域信息）
	def raidMsg(self):
		print "采集阵列信息"
		data = self.conn.EnumerateInstances('HuaSy_DiskStoragePool')
		for x in data:
			#id = x['InstanceID'].split(':')[0] + '_' + x['ElementName']
			id = x['InstanceID']
			self.composeContent('raid.name[{id}]'.format(id=id), x['ElementName']) # 名称
			self.composeContent('raid.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) # 总容量
			self.composeContent('raid.size.used[{id}]'.format(id=id), x['RemainingManagedSpace']) #已使用容量
			self.composeContent('raid.size.free[{id}]'.format(id=id), x['TotalManagedSpace'] - x['RemainingManagedSpace'] ) #
			self.composeContent('raid.size.available[{id}]'.format(id=id), x['HuaSyAvailableCapacity']) # 未分配的空闲容量
			self.composeContent('raid.operational.status[{id}]'.format(id=id), x['OperationalStatus']) # 运行状态
			self.composeContent('raid.status[{id}]'.format(id=id), x['HealthState']) # 健康状态
			#self.composeContent('raid.pool.id[{id}]'.format(id=id), x['PoolID'].split('_')[-1]) # 存储ID 这是一个字符PD_0,要处理下

	# 存储池所在的磁盘域
	def poolInRaid(self):
		cs_paths = conn.EnumerateInstanceNames('HuaSy_ConcreteStoragePool')
		for cs_path in cs_paths:
		cs_inst = conn.GetInstance(cs_path)
		dmsg = conn.Associators(cs_inst.path,'HuaSy_AllocatedFromStoragePool','HuaSy_DiskStoragePool')
		if len(dmsg)>0:
			self.composeContent('pool.in.raid[{id}]'.format(id=cs_path['InstanceID']), dmsg[0]['ElementName']) # 存储池所在的磁盘域

	#硬盘信息
	"""
		HuaSy_DiskDrive 基本信息
		HuaSy_DiskExtent 容量
		HuaSy_DiskPackag 物理信息
	"""
	def diskMsg(self):
		print "采集硬盘信息"
		data = self.conn.EnumerateInstances('HuaSy_DiskDrive')
		for x in data:
			id = x['DeviceID']
			self.composeContent('disk.name[{id}]'.format(id=id), x['ElementName']) # 名称
			self.composeContent('disk.type[{id}]'.format(id=id), x['Caption']) # 标题来当类型
			self.composeContent('disk.encryption[{id}]'.format(id=id), x['Encryption']) # 加密类型 0：未加密
			self.composeContent('disk.status[{id}]'.format(id=id), x['EnabledState']) # 状态 2：正常，其它 未知
			self.composeContent('disk.operational.status[{id}]'.format(id=id), x['OperationalStatus'][0]) # 
		data = self.conn.EnumerateInstances('HuaSy_DiskExtent')
		for x in data:
			id = x['DeviceID']
			self.composeContent('disk.blocks.number[{id}]'.format(id=id), x['NumberOfBlocks']) #  块数
			self.composeContent('disk.blocks.size[{id}]'.format(id=id), x['BlockSize']) # 块大小 4K 
			self.composeContent('disk.size.total[{id}]'.format(id=id), x['NumberOfBlocks'] * x['BlockSize']) #  容量 
			
		data = self.conn.EnumerateInstances('HuaSy_DiskPackag')
		for x in data:
			id = x['Tag']
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
		data = self.conn.EnumerateInstances('HuaSy_StorageHardwareID ')
		names = []
		ids = {}
		tmp = {} #映射的远程wwpn,即启动器
		source = conn.EnumerateInstanceNames('HuaSy_StorageHardwareID') #
		for x in data:
			name = x['ElementName']
			id = x['InstanceID']
			ids[id] = name
			if name not in names:  # 
				names.append(name)
				self.composeContent('storagehost.name[{id}]'.format(id=id), name) #

				#操作系统,所属主机组,映射的LUN
				for s in source:
					if s['InstanceID'] == id:
						cs_inst = conn.GetInstance(s)
						#操作系统
						dmsg = conn.Associators(cs_inst.path,'HuaSy_ElementSettingData','HuaSy_StorageClientSettingData')
						if dmsg:
							self.composeContent('storagehost.type[{id}]'.format(id=id), dmsg[0]['ElementName']) #操作系统

						#所属主机组
						dmsg = conn.Associators(cs_inst.path,'HuaSy_MemberOfCollection','HuaSy_InitiatorMasKingGroup')
						if len(d)>0:
							self.composeContent('storagehost.hostgroup.name[{id}]'.format(id=id), dmsg[0]['ElementName']) #所属主机组

						#映射的LUN
						cs_inst = conn.GetInstance(cs_path)
						t1 = conn.AssociatorNames(cs_inst.path,'HuaSy_AuthorizedSubject','HuaSy_AuthorizedPrivilege')
						if len(t1)>0:
							t2 = conn.AssociatorNames(t1[0],'HuaSy_AuthorizedTarget','HuaSy_MaskingSCSIProtocolController')
							if t2:
								t3 = conn.Associators(t2[0],'HuaSy_ProtocolControllerForUnit','HuaSy_StorageVolume')
								if t3:
									luns = []
									for t in t3:
										luns.appen(t['ElementName'])
									if luns:
										self.composeContent('storagehost.mapped.luns[{id}]'.format(id=id), json.dump(luns)) #存储主机已映射卷列表
			#映射的远程wwpn,即启动器
			if tmp.has_key(id):
				pass
			else:
				tmp[id] = []
			tmp[id].append(x['StorageID']) # wwpn
		for x in tmp:#映射的远程wwpn,即启动器（光纤端口）
			self.composeContent('storagehost.ports.wwpns[{id}]'.format(id=x), json.dump(tmp[x])) #存储主机WWPN列表




	# 主机组信息
	def hostGroupMsg(self):
		print "采集主机组信息"
		data = self.conn.EnumerateInstances('HuaSy_InitiatorMaskingGroup')
		source = conn.EnumerateInstanceNames('HuaSy_InitiatorMasKingGroup')
		for x in data:
			id = x['InstanceID']
			name = x['ElementName']
			self.composeContent('storagehg.name[{id}]'.format(id=name), name) #  主机组名称
			self.composeContent('storagehg.id[{id}]'.format(id=name), id) #  主机组名称
			#主机组下所有主机
			for s in source:
				if s['InstanceID'] == id:
					cs_inst = conn.GetInstance(s)
					dmsg = conn.Associators(cs_inst.path,'HuaSy_MemberOfCollection','HuaSy_StorageHardwareID')
					tmp = set()
					for d in dmsg:
						tmp.add(d['ElementName'])
					self.composeContent('storagehg.host.name[{id}]'.format(id=name), json.dump(list(tmp))) #  主机组下所有主机



	def LunMsg(self):
		print "采集LUN信息"
		data = self.lunDict
		for d in data:
			x = data[d]
			id = x['DeviceID']
			self.composeContent('lun.name[{id}]'.format(id=id), x['ElementName']) # 名称
			self.composeContent('lun.size.total[{id}]'.format(id=id), x['NumberOfBlocks'] * x['BlockSize']) #
			self.composeContent('lun.blocks.number[{id}]'.format(id=id), x['NumberOfBlocks']) #
			self.composeContent('lun.blocks.size[{id}]'.format(id=id), x['BlockSize']) #
			self.composeContent('lun.operational.status[{id}]'.format(id=id), x['OperationalStatus']) #
			self.composeContent('lun.name[{id}]'.format(id=id), x['ThinlyProvisioned']) # 是否是精简卷
			self.composeContent('lun.name[{id}]'.format(id=id), x['NoSinglePointOfFailure']) # 无单点故障
			self.composeContent('lun.wwn[{id}]'.format(id=id), x['Name']) # lun wwn 

		# LUN 映射的主机
		cs_paths = conn.EnumerateInstanceNames('HuaSy_StorageVolume')
		for cs_path in cs_paths:
			cs_inst = conn.GetInstance(cs_path)
			t1 = conn.AssociatorNames(cs_inst.path,'HuaSy_ProtocolControllerForUnit','HuaSy_MaskingSCSIProtocolController')
			if t1:
				t2 = conn.AssociatorNames(t1[0],'HuaSy_AuthorizedTarget','HuaSy_AuthorizedPrivilege') # 多个
				hosts = set()
				for o in t2:
					t3 = conn.Associators(o,'HuaSy_AuthorizedSubject','HuaSy_StorageHardwareID')
					hosts.add(t3[0]['ElementName'])
				self.composeContent('lun.mapped.host[{id}]'.format(id=cs_path['DeviceID']), json.dump(list(hosts)))# LUN 映射的主机


		for cs_path in cs_paths:
			cs_inst = conn.GetInstance(cs_path)
			#lun所在lun组
			dmsg = conn.Associators(cs_inst.path,'HuaSy_OrderedMemberOfCollection','HuaSy_DeviceMaskingGroup')
				if len(d)>0:
					self.composeContent('lun.in.group[{id}]'.format(id=cs_path['DeviceID']), dmsg[0]['ElementName']) # lun 所在 lun组

			#lun所属存储池
			dmsg = conn.Associators(cs_inst.path,'HuaSy_AllocatedFromStoragePool','HuaSy_ConcreteStoragePool')
			if len(dmsg)>0:
				self.composeContent('lun.pool.name[{id}]'.format(id=cs_path['DeviceID']), dmsg[0]['ElementName'])#lun所属存储池


	def LunGroupMsg(self):
		print "采集LUN信息"
		data = self.conn.EnumerateInstances('HuaSy_DeviceMaskingGroup')
		for d in data:
			x = data[d]
			id = x['InstanceID']
			self.composeContent('lg.name[{id}]'.format(id=id), x['ElementName']) # 名称



ip = '10.142.88.7'
user = 'smis_admin'
pwd = 'Admin@12'
host = 'test'
port = 10051
proxy = '10.142.88.7'
fun = 'msg'
h = Hw6800v3(ip,user,pwd,host,port,proxy,fun):
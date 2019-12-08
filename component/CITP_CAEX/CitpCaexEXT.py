import traceback
import struct
import re
from functools import reduce

class CITP_Content:
	CITP = 1347701059
	PINF = 1179535696
	PLOC = 1668238416
	CAEX = 1480933699

class CAEX_Content:
	NACK = 0xFFFFFFFF
	GetLaserFeedList	= 196864 # 0x00030100
	LaserFeedList		= 196865 # 0x00030101
	LaserFeedControl	= 196866 # 0x00030102
	LaserFeedFrame		= 197120 # 0x00030200 

class CitpCaexEXT:
	
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.WORKMODE = 'DEBUG' # 'RELEASE'
		self.ver = '0.8'
		self.ownerComp.par.Version = self.ver

		# -------- internal ops -------------------
		self.tcpOp = op('tcpip1')
		self.udpOp = op('udpin1')
		self.posDataOp = op('pos_chan_data')			# operator that contain xy channels for all inputs.  

		# -------- Init custom parameters ---------
		self.netActive 	= self.toggleHandler(self.ownerComp.par.Active.val)
		self.sourceKey 	= int(self.ownerComp.par.Id) # 0x45444f43
		self.udp_ip 	= self.checkIp(self.ownerComp.par.Ip.val)
		self.udp_port 	= int(self.ownerComp.par.Port.val)
		self.tcp_ip		= self.checkIp(self.ownerComp.par.Tcpip.val)
		self.feedName 	= self.ownerComp.par.Feedname.val

		# -------- Internal variables ------------
		self.onCookCounter = 0
		self.citp_header_keys = ['Cookie','VerMaj','VerMin','Rind','MessSize','MessPartCnt','MessPart','ContentType']
		self.caex_LaserFeedFrame_header_b = self.citp_caex_header_set(CAEX_Content.LaserFeedFrame) + struct.pack('<I',self.sourceKey)
		self.fl_capture_connection = False
		self.feed = 0
		self.nfeeds = 0
		self.data2send = bytes()

		# -------- Set default state ------------
		self.ownerComp.par.Fps = 0
		self.ownerComp.par.Status = 'No connection'

		self.udpOp.par.address 	= self.udp_ip
		self.udpOp.par.port 	= self.udp_port

		self.tcpOp.par.address = self.tcp_ip

		if self.netActive:
			self.udpOp.par.active = 1
		else:
			self.udpOp.par.active = 0
			self.tcpOp.par.active = 0

		self.setParVisib(not self.netActive)
		#keys = {'Cookie','VerMaj','VerMin','Rind','MessSize','MessPartCnt','MessPart','ContentType'}
		#self.citp_header = dict.fromkeys(keys,0)
	#_______________________________
	#Command execution
	#_______________________________
	def Execute(self, message):
		# takes all commands from interface and routes it to the appropriate function calls
		function_name = message.get('parameter_name')
		function_args = message.get('parameter_value', 'none')
		function = getattr(self, function_name)
	
		function(function_args)
		
		
		
# =============================== Settings ==========================================================

	def Active(self, val = 'none'):
		self.netActive = self.toggleHandler(val)
		
		self.setParVisib(not self.netActive)

		self.fl_capture_connection = False
		self.ownerComp.par.Fps = 0
		self.ownerComp.par.Status = 'No connection'

		if self.netActive:
			self.udpOp.par.active = 1
		else:
			self.udpOp.par.active = 0
			self.tcpOp.par.active = 0

		self.compPrint('Result: {}'.format(self.netActive))


	def Id(self, val = 'none'):
		self.compPrint(val)
		self.sourceKey = int(val)
		self.caex_LaserFeedFrame_header_b = self.citp_caex_header_set(CAEX_Content.LaserFeedFrame) + struct.pack('<I',self.sourceKey)
	
	def Tcpip(self, val = 'none'):
		self.compPrint(val)
		self.tcp_ip = self.checkIp(val)
		self.tcpOp.par.address = self.tcp_ip

	def Ip(self, val = 'none'):
		self.compPrint(val)
		self.udp_ip = self.checkIp(val)
		self.udpOp.par.address = self.udp_ip

	def Port(self, val = 'none'):
		self.compPrint(val)
		self.udp_port = int(val)
		self.udpOp.par.port = self.udp_port

	def Status(self, val = 'none'):
		pass 

	def Fps(self, val = 'none'):
		pass

	def Feedname(self, val = 'none'):
		self.compPrint(val)
		self.feedName = val

# =============================== Misc page =========================================================
	def Version(self, val = 'none'):
		pass
	
	def Help(self, val = 'none'):
		op('help').openViewer()
		pass

# ================================ Public ===========================================================

	def ScriptpOp_onSetupParameters(self, scriptOp):
		#self.compPrint(scriptOp)
		pass
	
	def ScriptpOp_onPulse(self,par):
		self.compPrint(par)
		pass
	
	def ScriptpOp_onCook(self,scriptOp):
		if self.fl_capture_connection: #self.netActive: # self.fl_capture_connection

			srcOp = scriptOp.inputs[0]
			nf = self.nfeeds
			for i in range(0,nf):	# because we need to check not-numered channels
				X = srcOp[2*i]
				Y = srcOp[2*i+1]

				try:
					feedInd = re.findall(r'\d+', X.name).pop()
				except IndexError:
					feedInd = -1		

				if feedInd == -1:				
					R = srcOp['r']
					G = srcOp['g']
					B = srcOp['b']
				else:
					ind = str(feedInd)
					R = srcOp['r'+ind]
					G = srcOp['g'+ind]
					B = srcOp['b'+ind]

				data, pointC = self.citp_caex_laserDataPreProc_2(X,Y,R,G,B) # prepare byte array data
				
				feedInfo = struct.pack('<BIH', i, self.onCookCounter, pointC)
				message = self.citp_Set_message_Size(self.caex_LaserFeedFrame_header_b + feedInfo + data)
				
				self.udpOp.sendBytes(message)

			if not (self.onCookCounter%(300*project.cookRate)):
				self.compPrint(self.onCookCounter, len(message), pointC)

			self.onCookCounter += 1	
		else:
			self.onCookCounter = 0
		pass

	def UdpReceiverHandler(self,message, bytes, peer):
		message = 'Peer: ' + peer.address + ' ' + str(peer.port)
		#self.compPrint(message,'Data ' + bytes.decode('cp1250'), 'SIZE: '+ str(len(bytes)))
		tcpport = self.citp_Ploc_parser(bytes)
		if tcpport == 0:
			self.tcpOp.par.active = 0 
			self.fl_capture_connection = False
			self.ownerComp.par.Fps = 0
			self.ownerComp.par.Status = 'No connection'

		else:
			self.tcpOp.par.port = tcpport
			self.tcpOp.par.active = 1
	
	def TcpReceiverHandler(self,message, bytes, peer):
		message = 'Peer: ' + peer.address + ' ' + str(peer.port)
		caex_message = 'none'
		CaexContentCode, index = self.citp_caex_parser(bytes)
		if index > -1:
			if CaexContentCode == CAEX_Content.NACK:
				caex_message = 'NACK'
				pass

			elif CaexContentCode == CAEX_Content.GetLaserFeedList:
				caex_message = 'GetLaserFeedList'
				self.citp_caex_LaserFeedList()
				pass

			elif CaexContentCode == CAEX_Content.LaserFeedList:
				caex_message = 'LaserFeedList'
				pass

			elif CaexContentCode == CAEX_Content.LaserFeedControl:
				caex_message = 'LaserFeedControl' 
				self.feed, frameRate = self.citp_caex_LaserFeedControl( bytes[index:index+26] )
				self.ownerComp.par.Fps = int(frameRate)				
				if frameRate != 0:
					self.fl_capture_connection = True
					self.ownerComp.par.Status = 'Active'

			elif CaexContentCode == CAEX_Content.LaserFeedFrame:
				caex_message = 'LaserFeedFrame' 
				pass

		self.compPrint(message,bytes, 'SIZE: '+ str(len(bytes)),'CAEX content = ' + caex_message)

	def InputFeedsNChangeHandler(self):
		self.citp_caex_LaserFeedList()
	
# ----------------   CITP  ----------------------------------------------------------------------
	def citp_header_parser(self,rdata):
		data = struct.unpack('<IBBHIHHI', rdata)
		citp_header = dict(zip(self.citp_header_keys, data))
		#self.compPrint('Incoming data size: ' + str(len(rdata)),data)	
		if citp_header['Cookie'] == CITP_Content.CITP:
			return citp_header['ContentType']
		else:	
			return 0

	def citp_Pinf_header_parser(self, data):
		pinf_Content = [0]
		if self.citp_header_parser(data[0:20]) == CITP_Content.PINF:
			message = 'CITP PINF mesage received'
			pinf_Content = struct.unpack('<I',data[20:24])
		else:
			message = 'Its not a PINF message'
		#self.compPrint(message,'pinf_Content = {}'.format(pinf_Content[0]))
		return pinf_Content[0]

	def citp_Ploc_parser(self, data):
		citp_tcpPort = [0]
		cnt = self.citp_Pinf_header_parser(data)
		if cnt == CITP_Content.PLOC:
			message = 'CITP PLOC mesage received'
			citp_tcpPort = struct.unpack('<H',data[24:26])
		else:
			message = 'Its not a PLOC message'
		#self.compPrint(message,'citp_tcpPort = {}'.format(citp_tcpPort[0]))
		return citp_tcpPort[0]
	
	def citp_caex_parser(self, data):
		content = 0
		index = -1
		citp_header_size = 20
		message = 'NO CAEX message'

		for i in range(0,len(data)-citp_header_size+1):
			if self.citp_header_parser(data[i:i+citp_header_size]) == CITP_Content.CAEX:
				caex_content_index = i+citp_header_size
				content = struct.unpack('<I', data[caex_content_index:caex_content_index+4])[0]
				message = 'CAEX message found. Ind = ' + str(i)
				index = i
				break 
		
		self.compPrint(message, 'caex content = ' + str(content))
		return content, index

	def citp_caex_LaserFeedList(self):
		caex_header_b = self.citp_caex_header_set(CAEX_Content.LaserFeedList) 

		self.nfeeds = int(self.posDataOp.numChans/2)	# its 2 channels for every feed - x and y
		l_usc = 0
		feedName_data = bytearray()

		for i in range(0,self.nfeeds):
			feedName_u = self.feedName.encode('UTF-16LE')+ str(i).encode('UTF-16LE') + b'\x00\x00'
			l_usc = l_usc + len(feedName_u)
			feedName_data = feedName_data + feedName_u

		body_form = '<IB{}s'.format(l_usc)
		body = struct.pack(body_form,self.sourceKey, self.nfeeds, feedName_data) 
		
		message = self.citp_Set_message_Size(caex_header_b + body)
		
		self.compPrint('N feeds: '+ str(self.nfeeds),'FeedName Unicode len: '+ str(l_usc), 'Message: ',message)
		self.tcpOp.sendBytes(message)
		#op('tcpip2').sendBytes(message)

	def citp_caex_LaserFeedControl(self, rdata):
		l = len(rdata)
		LaserFeedInfo = struct.unpack('<BB',rdata[-2:])
		feed = LaserFeedInfo[0]
		frameRate = LaserFeedInfo[1]
		self.compPrint(rdata, 'SIZE = ' + str(l),'LaserFeedInfo. Feed: ' + str(feed) + ', FrameRate: ' + str(frameRate))
		return feed, frameRate	

	def citp_caex_header_set(self,ContentCode):

		citp_header_b = self.citp_header_set(CITP_Content.CAEX)
		caex_content_b = struct.pack('<I',ContentCode)
		caex_header_b = citp_header_b + caex_content_b

		self.compPrint('ContentCode = ' + str(ContentCode), caex_header_b)
		return caex_header_b

	def citp_header_set(self, Content):
		#self.citp_header_keys = ['Cookie','VerMaj','VerMin','Rind','MessSize','MessPartCnt','MessPart','ContentType']
		hdr = dict.fromkeys(self.citp_header_keys,0)
		hdr['Cookie'] 		= CITP_Content.CITP
		hdr['VerMaj'] 		= 1
		hdr['VerMin'] 		= 0
		hdr['Rind']	 		= 0
		hdr['MessSize'] 	= 0
		hdr['MessPartCnt'] 	= 1
		hdr['MessPart']		= 0
		hdr['ContentType'] 	= Content
		
		self.compPrint('Content = ' + str(Content), hdr)
		return struct.pack('<IBBHIHHI',hdr['Cookie'],hdr['VerMaj'],hdr['VerMin'],hdr['Rind'],hdr['MessSize'],hdr['MessPartCnt'],hdr['MessPart'],hdr['ContentType'])

	def citp_Set_message_Size(self,message):
		size = len(message)
		size_b = struct.pack('<I',size)
		nMess = message[0:8] + size_b + message[12:]
		#self.compPrint('Message size = ' + str(size), type(nMess),'Return message size = ' + str(len(nMess)))
		return nMess
	
	def citp_caex_laserDataPreProc(self,X,Y,R,G,B):
			data = bytes()
			#self.compPrint('Execution')

			# print('len X = ' + str(len(X)))
			# print('len Y = ' + str(len(Y)))

			if ((R is None)or(G  is None)or(B  is None)):
			#	print('Color mode: Monochrome')
				numSmpl = min(len(X),len(Y))
				fl_monochrome = True

			else:
			#	print('len R = ' + str(len(R)))
			#	print('len G = ' + str(len(G)))
			#	print('len B = ' + str(len(B)))				
			#	print('Color mode: RGB')

				numSmpl = min(len(X),len(Y),len(R),len(G),len(B))
				fl_monochrome = False


			# print('N samples: ' + str(numSmpl))

			for i in range(0,numSmpl):
				Xint = int(X[i])
				Yint = int(Y[i])

				XlowByte = Xint%256	
				YlowByte = Yint%256

				Xnibble = (Xint//256)%16	
				Ynibble = (Yint//256)%16	
				XYnibble = Ynibble*16 + Xnibble

				if fl_monochrome:
					Color = 0xffff
				else:
					R5 = int(R[i])%32
					G6 = (int(G[i])%64)*32
					B5 = (int(B[i])%32)*2048
					Color = R5+G6+B5

				pdata = struct.pack('<BBBH',XlowByte,YlowByte,XYnibble,Color)
				data = data+pdata

			#	print(i)
			#	print(X[i], Xint, Y[i], Yint)
			#	print(XlowByte,YlowByte,XYnibble,Color)
			#	print(pdata)

			# print('Data len: ' + str(len(data)))
			# print(data)
			return data, numSmpl

	def citp_caex_laserDataPreProc_2(self,X,Y,R,G,B):
	
		if ((R is None)or(G  is None)or(B  is None)):
			numSmpl = min(len(X),len(Y))
			fl_monochrome = True

		else:
			numSmpl = min(len(X),len(Y),len(R),len(G),len(B))
			fl_monochrome = False

		Xlb = [ int(x)%256 for x in X.vals]
		Ylb = [ int(y)%256 for y in Y.vals]
		XYnb = list(map((lambda x,y: (int(x)//256) + (int(y)//256)*16 ), X.vals,Y.vals ))

		if fl_monochrome:
			Color = [0xffff for i in range(numSmpl)]
		else:
			Color = list(map((lambda r,g,b: int(r)+int(g)*32+int(b)*2048 ), R.vals,G.vals,B.vals ))

		data = reduce(lambda p,n: p+n, list(map( lambda x,y,z,w: struct.pack('<BBBH',x,y,z,w), Xlb,Ylb,XYnb,Color)))

		return data, numSmpl


	def Test(self):
		srcOp = op('testChop')
					
		X = srcOp['x']
		Y = srcOp['y']
		R = srcOp['r']
		G = srcOp['g']
		B = srcOp['b']
		
		self.citp_caex_laserDataPreProc(X,Y,R,G,B)

# ---------------- private ----------------------------------------------------------------------	

	def setConstOpVal(self,ConstanOP,channel_name,value):
		index = int(ConstanOP[channel_name].index)
		setattr(ConstanOP.par, 'value{}'.format(index), value)
	
	def pulseConstOpval(self,ConstanOP,channel_name,value = 1, width_s = 1):
		index = int(ConstanOP[channel_name].index)
		param = getattr(ConstanOP.par,'value{}'.format(index))
		param.pulse(value, seconds = width_s)
	
	def toggleHandler(self,tgl):
		tglDict = {'off':0,'False':0,'on':1,'True':1,False:0,True:1}
		return tglDict.get(tgl,0)

	def compPrint(self, *message):
		if self.WORKMODE == 'DEBUG': 
			compName = self.ownerComp.name
			func = traceback.extract_stack(None, 2)[0][2]
			print('\nop:\t\t\t{}.\nfunc:\t\t{}.\nmessage:\t{}'.format(compName,func,message))
		elif self.WORKMODE == 'RELEASE':
			pass 
	
	def checkIp(self,addr):
		if addr not in ['localhost', 'LOCALHOST', 'Localhost']:
			ipMatchExpr = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
			if not re.match(ipMatchExpr,addr):
				ui.messageBox('Warning', 'INCORRECT IP')
				#self.ownerComp.addScriptErrors('INCORRECT IP')
				#print('\n******************\nWRONG IP\n******************\n')
				return '0.0.0.0'
		return addr	
	
	
	def setParVisib(self, state):
		self.ownerComp.par.Id.enable 		= state
		self.ownerComp.par.Ip.enable 		= state
		self.ownerComp.par.Port.enable 		= state
		self.ownerComp.par.Feedname.enable 	= state
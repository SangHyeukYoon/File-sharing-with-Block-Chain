import os
import sys
import atexit
import socket
import threading
import time
from uuid import uuid4

from message import Message
from BlockChain import BlockChain


class P2P:
    def __init__(self, PORT, nodeID, blockChain=None, N_HOST=None, N_PORT=None):
        self.nodeID = nodeID
        self.blockChain = blockChain

        self.nodeIn = []
        self.nodeOut = []

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('', int(PORT)))
        self.s.listen()

        self.HOST = socket.gethostbyname(socket.gethostname())
        self.PORT = PORT

        self._recv_block = []

        atexit.register(self._close)

        if (N_HOST != None and N_HOST != '0') and (N_PORT != None and N_HOST != '0'):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((N_HOST, int(N_PORT)))
            except Exception as e:
                print(e)
            else:
                msg = Message(s)

                # send own address
                msg.Send((self.HOST, self.PORT, self.nodeID))
                nodeID, _ = msg.Receive()

                node = {
                    'msg': msg,
                    'HOST': N_HOST,
                    'PORT': N_PORT,
                    'nodeID': nodeID
                }

                # get block chains
                self.blockChain.chains, _ = msg.Receive()

                self.nodeOut.append(node)

                print('{}:{} is connected'.format(N_HOST, N_PORT))

    def Run(self):
        try:
            self.listenPhase = self.ListenPhase()
            self.recvPhase = self.RecvPhase()

            while True:
                command = input('send or conn: ')

                if command == 'send':
                    print('send data...')
                    self.SendData('hello nodes!')
                elif command == 'conn':
                    HOST = input('HOST: ')
                    PORT = input('PORT: ')

                    self.MakeConnection(HOST, PORT)
        except KeyboardInterrupt:
            print('\nclose...')
            exit(0)
        except Exception as e:
            print(e)

    def ListenPhase(self):
        # make _listen_phase thread
        listenPhase = threading.Thread(target=self._listen_phase)
        listenPhase.daemon = True
        listenPhase.start()

        return listenPhase
    
    def RecvPhase(self):
        # make _recv_phase thread
        recvPhase = threading.Thread(target=self._recv_phase)
        recvPhase.daemon = True
        recvPhase.start()

        return recvPhase
    
    def SendData(self, data, dataType='message'):
        for node in self.nodeIn:
            msg = node['msg']

            try:
                msg.Send(data, dataType)
            except Exception as e:
                print(e)
        
        for node in self.nodeOut:
            msg = node['msg']

            try:
                msg.Send(data, dataType)
            except Exception as e:
                print(e)
    
    def MakeConnection(self, HOST, PORT):
        # check if addres is mine. 
        # TODO: change to (HOST == '127.0.0.1' or self.HOST != HOST) and self.PORT != PORT
        if self.PORT != PORT:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((HOST, int(PORT)))
            except Exception as e:
                print(e)
            else:
                msg = Message(s)

                # send own address
                msg.Send((self.HOST, self.PORT, self.nodeID))

                # get node id
                nodeID, _ = msg.Receive()

                node = {
                    'msg': msg,
                    'HOST': HOST,
                    'PORT': PORT,
                    'nodeID': nodeID
                }

                # get block chains
                self.blockChain.chains, _ = msg.Receive()

                self.nodeOut.append(node)

                print('{}:{} is connected'.format(HOST, PORT))
    
    def BlockUpdator(self):
        # make _listen_phase thread
        blockUpdator = threading.Thread(target=self._block_updator)
        blockUpdator.daemon = True
        blockUpdator.start()

        return blockUpdator
    
    def _listen_phase(self):
        # listening connections. 
        while True:
            try:
                conn, addr = self.s.accept()
                print('connected to {}'.format(addr))

                # add socket as message object
                msg = Message(conn)

                address, _ = msg.Receive()
                msg.Send(self.nodeID)

                node = {
                    'msg': msg,
                    'HOST': address[0],
                    'PORT': address[1],
                    'nodeID': address[2]
                }

                self.nodeIn.append(node)

                msg.Send(self.blockChain.chains, 'init_chains')

                self.SendData(address, 'update_node')
            except:
                pass
    
    def _recv_phase(self):
        while True:
            try:
                for node in self.nodeIn:
                    msg = node['msg']
                    data, header = msg.Receive(1.)      # set time out as 1s. 

                    # if get data
                    if data != None:
                        # if get message, terminate
                        if header['msgType'] == 'terminate':
                            msg.sock.close()
                            self.nodeIn.remove(node)
                        else:
                            self._msg_handler(data, header)

                for node in self.nodeOut:
                    msg = node['msg']
                    data, header = msg.Receive(1.)      # set time out as 1s. 

                    # if get data
                    if data != None:
                        # if get message, terminate
                        if header['msgType'] == 'terminate':
                            msg.sock.close()
                            self.nodeOut.remove(node)
                        else:
                            self._msg_handler(data, header)
            except:
                pass
            else:
                time.sleep(1.)
    
    def _msg_handler(self, data, header):
        if header['msgType'] == 'update_node':
            self._update_node(data)
        elif header['msgType'] == 'update_block':
            self._recv_block.append(data)
        else:
            print(data)
    
    def _update_node(self, addr):
        if not (addr[0:2] in [[node['HOST'], node['PORT']] for node in (self.nodeIn + self.nodeOut)]):
            # check if address is mine. 
            # TODO: change to (addr[0] == '127.0.0.1' or self.HOST != addr[0]) and self.PORT != addr[1]
            if self.PORT != addr[1]:
                self.MakeConnection(addr[0], addr[1])
    
    def _block_updator(self):
        while True:
            timeStamp = int(time.time())
            if timeStamp % 10 == 0:
                time.sleep(.5)
                while len(self._recv_block) != 0:
                    maxTrans = 0
                    maxBlock = None
                    for block in self._recv_block:
                        if len(block['transactions']) > maxTrans and int(block['timeStamp']) < timeStamp:
                            maxTrans = len(block['transactions'])
                            maxBlock = block
                    
                    if maxBlock != None and self.blockChain.ValidProof(maxBlock):
                        self.blockChain.UpdateBlock(maxBlock)
                        print('update block!')

                        # if update own transaction, empty it. 
                        if maxBlock['transactions'] == self.blockChain.transactions:
                            print('update my block')
                            self.blockChain.transactions = []
                        
                        for block in self._recv_block:
                            if int(block['timeStamp']) < timeStamp:
                                self._recv_block.remove(block)
                        
                        break
                        
                    elif maxBlock != None:
                        self._recv_block.remove(maxBlock)
            else:
                time.sleep(.2)
    
    def _close(self):
        self.SendData('t', 'terminate')

        time.sleep(1)

        for node in self.nodeIn:
            msg = node['msg']
            msg.sock.close()
        
        for node in self.nodeOut:
            msg = node['msg']
            msg.sock.close()
        
        self.s.close()


if __name__ == '__main__':
    nodeID = str(uuid4()).replace('-', '')

    if len(sys.argv) == 2:
        p2p = P2P(sys.argv[1], nodeID)
        p2p.Run()
    elif len(sys.argv) > 3:
        p2p = P2P(sys.argv[1], nodeID, sys.argv[2], sys.argv[3])
        p2p.Run()


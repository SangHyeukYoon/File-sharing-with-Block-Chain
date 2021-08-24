import os
import sys
import atexit
import socket
import threading
import time
from pprint import pprint
from uuid import uuid4

from message import Message
from BlockChain import BlockChain
from p2p import P2P


class Node:
    def __init__(self, PORT, N_HOST=None, N_PORT=None, defaultDir='server/'):
        self.defaultDir = defaultDir

        self.nodeID = str(uuid4()).replace('-', '')     # unique number for node

        self.blockChain = BlockChain(self.nodeID, self.defaultDir)
        self.p2p = P2P(PORT, self.nodeID, self.blockChain, N_HOST, N_PORT)

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('', int(PORT)+1))
        self.s.listen()

        atexit.register(self._close)

    def Run(self):
        print('start node')

        try:
            self.p2p.ListenPhase()
            self.p2p.RecvPhase()
            self.p2p.BlockUpdator()

            thread = threading.Thread(target=self.ListenClient)
            thread.daemon = True
            thread.start()

            while True:
                command = input('[conn]ect new node or [print] all blocks or [node] print all nodes: ')
                if command == 'conn':
                    HOST = input('HOST: ')
                    PORT = input('PORT: ')

                    self.p2p.MakeConnection(HOST, PORT)

                elif command == 'print':
                    pprint(self.blockChain.chains)
                
                elif command == 'node':
                    pprint(self.p2p.nodeIn)
                    pprint(self.p2p.nodeOut)
        
        except KeyboardInterrupt:
            print('\nclose..')
            exit(0)
        except Exception as e:
            print(e)
        
    def ListenClient(self):
        while True:
            try:
                conn, addr = self.s.accept()

                print('connected to {}'.format(addr))

                thread = threading.Thread(target=self.HandleClient, args=(conn,))
                thread.daemon = True
                thread.start()
            except:
                pass

    def HandleClient(self, sock):
        ms = Message(sock, self.defaultDir)
        clientID, _ = ms.Receive()

        while True:
            d, header = ms.Receive()

            if d == 'upload':
                fileInfo, _ = ms.Receive()

                if fileInfo != 'err':
                    ms.ReceiveFile(fileInfo['fileName'], fileInfo['fileLength'])
                    trans = self.blockChain.SubmitTransaction(fileInfo['fileName'], clientID)
                    ms.Send(trans)

                    try:
                        os.rename(self.defaultDir+fileInfo['fileName'], 
                            self.defaultDir+trans['fileHash']+'-'+fileInfo['fileName'])
                    except:
                        pass

                    if self.blockChain.getTransactionCount() > 0:
                        if self.blockChain.getBlockCount() == 0:
                            block = self.blockChain.CreateBlock('00000000')
                        else:
                            prevHash = self.blockChain.Hash(self.blockChain.getLastBlock())
                            block = self.blockChain.CreateBlock(prevHash)

                        self.p2p.SendData(block, 'update_block')
                        # add own block
                        self.p2p._recv_block.append(block)

            elif d == 'download':
                searchMethod, _ = ms.Receive()     # file name or file hash
                value, _ = ms.Receive()

                if searchMethod == 'name':
                    fileBlock = self.blockChain.SearchByName(value)
                elif searchMethod == 'hash':
                    fileBlock = self.blockChain.SearchByFileHash(value)

                if fileBlock == None:
                    ms.Send('None', 'no_file')
                # check if file exist
                elif os.path.exists(self.defaultDir+fileBlock['fileHash']+'-'+fileBlock['fileName']):
                    ms.Send(fileBlock)
                    ms.SendFile(fileBlock['fileHash']+'-'+fileBlock['fileName'])
                else:
                    # if other node has the file, route path. 
                    nodeID = fileBlock['nodeID']
                    if nodeID in [node['nodeID'] for node in (self.p2p.nodeIn + self.p2p.nodeOut)]:
                        for node in (self.p2p.nodeIn + self.p2p.nodeOut):
                            if node['nodeID'] == nodeID:
                                ms.Send((node['HOST'], node['PORT']), 'route_node')
                                break
                    else:
                        ms.Send('None', 'no_node')
            
            elif d == '_download':
                searchMethod, _ = ms.Receive()     # file name or file hash
                value, _ = ms.Receive()

                if searchMethod == 'name':
                    fileBlock = self.blockChain.SearchByName(value)
                elif searchMethod == 'hash':
                    fileBlock = self.blockChain.SearchByFileHash(value)

                if fileBlock == None:
                    ms.Send('None')
                else:
                    # check if file exist
                    if os.path.exists(self.defaultDir+fileBlock['fileHash']+'-'+fileBlock['fileName']):
                        ms.Send(fileBlock)
                        ms.SendFile(fileBlock['fileHash']+'-'+fileBlock['fileName'])
                    else:
                        ms.Send('None')
                
                # send file once. 
                sock.close()

                break

            elif d == 'print':
                ms.Send(self.blockChain.chains)
            
            elif d == 'history':
                searchMethod, _ = ms.Receive()     # file name or file hash
                value, _ = ms.Receive()

                if searchMethod == 'name':
                    fileBlock = self.blockChain.SearchHistoryByName(value)
                elif searchMethod == 'hash':
                    fileBlock = self.blockChain.SearchHistoryByFileHash(value)
                
                ms.Send(fileBlock)
            
            elif header['msgType'] == 'terminate':
                sock.close()

                break

            else:
                print(d)

    def _close(self):
        self.s.close()
        
        sys.exit(0)


if __name__ == '__main__':
    if len(sys.argv) > 4:
        node = Node(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
        node.Run()

    elif len(sys.argv) > 3:
        node = Node(sys.argv[1], sys.argv[2], sys.argv[3])
        node.Run()
    
    elif len(sys.argv) > 1:
        node = Node(sys.argv[1])
        node.Run()
    
    


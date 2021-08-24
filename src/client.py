import os
import sys
import atexit
import socket
from pprint import pprint
import hashlib
from uuid import uuid4
import time

from message import Message


HOST = '127.0.0.1'      # The server's IP address. 
PORT = 3000            # The port used by server. 


class Client:
    def __init__(self, HOST, PORT, defaultDir='client/'):
        self.HOST = HOST
        self.PORT = PORT
        self.defaultDir = defaultDir

        self.nodeID = str(uuid4()).replace('-', '')     # unique number for node

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        atexit.register(self._close)
    
    def Run(self):
        try:
            self.s.connect((self.HOST, int(self.PORT)+1))

            ms = Message(self.s, self.defaultDir)
            ms.Send(self.nodeID)

            print('[upload]: upload file')
            print('[download]: download file')
            print('[print]: print blocks')
            print('[history]: print history')
            print()

            while True:
                command = input('Enter command: ')
                ms.Send(command)

                if command == 'upload':
                    fileName = input('Enter file name: ')

                    if os.path.exists(self.defaultDir+fileName):
                        ms.SendFile(fileName)

                        block, _ = ms.Receive()

                        pprint(block)
                    else:
                        print('no such file!')
                        ms.Send('err')

                elif command == 'download':
                    while not(command == 'name' or command == 'hash'):
                        command = input('Enter search method. [name] or [hash]: ')
                    ms.Send(command)

                    if command == 'name':
                        value = input('Enter file name to download: ')
                    else:
                        value = input('Enter file hash to download: ')

                    ms.Send(value)

                    fileBlock, hdr = ms.Receive()

                    if hdr['msgType'] == 'no_file':
                        print('No such file.')
                    elif hdr['msgType'] == 'route_node':
                        print('connect to other node {}:{}'.format(fileBlock[0], fileBlock[1]))
                        self._recv_file_from_other_node(fileBlock[0], fileBlock[1], command, value)
                    elif hdr['msgType'] == 'no_node':
                        print('There is no node with the file.')
                    else:
                        fileInfo, _ = ms.Receive()
                        ms.ReceiveFile(fileBlock['fileName'], fileInfo['fileLength'])

                        if fileBlock['fileHash'] == self._get_file_hash(fileBlock['fileName']):
                            print('get valid file!')
                        else:
                            print('get wrong file!')
                            os.remove(self.defaultDir+fileBlock['fileName'])
                
                elif command == 'print':
                    blocks, _ = ms.Receive()
                    pprint(blocks)
                
                elif command == 'history':
                    while not(command == 'name' or command == 'hash'):
                        command = input('Enter search method. [name] or [hash]: ')
                    ms.Send(command)

                    if command == 'name':
                        value = input('Enter file name to find history: ')
                    else:
                        value = input('Enter file hash to find history: ')

                    ms.Send(value)

                    his, _ = ms.Receive()

                    pprint(his)
                
        except Exception as e:
            print(e)
        except KeyboardInterrupt:
            ms.Send('/quit', 'terminate')
            time.sleep(1.)

            sys.exit(0)
    
    def _recv_file_from_other_node(self, HOST, PORT, command, value):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, int(PORT)+1))

            print('connected')

            ms = Message(s, self.defaultDir)
            ms.Send(self.nodeID)

            # download file protocol
            ms.Send('_download')
            ms.Send(command)
            ms.Send(value)

            fileBlock, _ = ms.Receive()
            if fileBlock == 'None':
                print('download file failed!')
                s.close()

                return
            else:
                fileInfo, _ = ms.Receive()
                ms.ReceiveFile(fileBlock['fileName'], fileInfo['fileLength'])

                if fileBlock['fileHash'] == self._get_file_hash(fileBlock['fileName']):
                    print('get valid file!')
                else:
                    print('get wrong file!')
                    os.remove(self.defaultDir+fileBlock['fileName'])
        
        except:
            print('download file failed!')
            s.close()

            return
        
        else:
            s.close()

            return
        
    def _get_file_hash(self, fileName, blockSize=65536):
        '''
            _get_file_hash:
                Make md5 checksum of uploaded file. 

            parameters:
                filname: string -> name of uploaded file. 
                blockSize: integer -> the size of block when read the file

            exceptions:
                OSError -> file open error
        '''
        hasher = hashlib.md5()

        try:
            f = open(self.defaultDir+fileName, 'rb')
        except:
            # can not open file
            raise

        with f:
            buf = f.read(blockSize)
            while buf:
                hasher.update(buf)

                buf = f.read(blockSize)

        return hasher.hexdigest()

    def _close(self):
        print('\nclose')
        self.s.close()


if __name__ == '__main__':
    if len(sys.argv) > 3:
        client = Client(sys.argv[1], sys.argv[2], sys.argv[3])
        client.Run()
    
    elif len(sys.argv) > 2:
        client = Client(sys.argv[1], sys.argv[2])
        client.Run()
    


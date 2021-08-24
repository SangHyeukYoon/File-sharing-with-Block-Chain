import os
import sys
import time

import hashlib
from uuid import uuid4

import json


class BlockChain:

    def __init__(self, nodeID, defaultDir='server/'):
        self.nodeID = nodeID
        self. defaultDir = defaultDir

        self.transactions = []
        self.chains = []
    
    def SubmitTransaction(self, fileName, uploaderID):
        '''
            SubmitTransaction:
                When file is uploaded, submit transaction using md5 checksum. 

            parameters:
                fileName: string -> name of uploaded file. 
                uploaderID: string(hexDigit) -> ID of uploader. 

            exceptions:
                file open error(_get_file_hash)
        '''

        # Check if file exists. 
        fileHash = self._get_file_hash(self.defaultDir + fileName)

        # make transaction
        transaction = {
            'nodeID': self.nodeID,
            'uploaderID': uploaderID,
            'fileName': fileName,
            'fileHash': fileHash
        }

        # append transaction
        self.transactions.append(transaction)

        return transaction
    
    def CreateBlock(self, prevHash):
        '''
            CreateBlock:
                create block, empty my transactions and return created block. 

            parameters:
                prevHash: hexDigit -> hash of previous block. 
        '''

        # make a block
        block = {
            'blockNum': len(self.chains)+1,
            'timeStamp': time.time(),
            'transactions': self.transactions,
            'prevHash': prevHash
        }

        # empty the transactions
        #self.transactions = []

        # append block
        #self.chains.append(block)

        return block
    
    def ValidProof(self, block):
        lastBlock = self.getLastBlock()
        if lastBlock == None:
            lastBlockHash = '00000000'
        else:
            lastBlockHash = self.Hash(lastBlock)

        if lastBlockHash == block['prevHash']:
            return True
        else:
            return False
    
    def UpdateBlock(self, block):
        self.chains.append(block)
    
    def Hash(self, block):
        '''
            Hash:
                Make hash of block. 
            
            parameters:
                block: dic -> block to make hash
        '''

        blockJson = json.dumps(block).encode()

        return hashlib.sha256(blockJson).hexdigest()
    
    def SearchByName(self, fileName):
        for i in range(len(self.chains)-1, -1, -1):
            for x in range(len(self.chains[i]['transactions'])-1, -1, -1):
                if self.chains[i]['transactions'][x]['fileName'] == fileName:
                    return self.chains[i]['transactions'][x]
        
        return None

    def SearchByFileHash(self, fileHash):
        for i in range(len(self.chains)-1, -1, -1):
            for x in range(len(self.chains[i]['transactions'])-1, -1, -1):
                if self.chains[i]['transactions'][x]['fileHash'] == fileHash:
                    return self.chains[i]['transactions'][x]
        
        return None
    
    def SearchHistoryByName(self, fileName):
        result = []
        for block in self.chains:
            for trans in block['transactions']:
                if trans['fileName'] == fileName:
                    result.append(trans)
        
        return result
    
    def SearchHistoryByFileHash(self, fileHash):
        result = []
        for block in self.chains:
            for trans in block['transactions']:
                if trans['fileHash'] == fileHash:
                    result.append(trans)
        
        return result
    
    def getTransactionCount(self):
        return len(self.transactions)
    
    def getBlockCount(self):
        return len(self.chains)
    
    def getLastBlock(self):
        if self.getBlockCount() == 0:
            return None
        else:
            return self.chains[self.getBlockCount()-1]
    
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
            f = open(fileName, 'rb')
        except:
            # can not open file
            raise

        with f:
            buf = f.read(blockSize)
            while buf:
                hasher.update(buf)

                buf = f.read(blockSize)

        return hasher.hexdigest()


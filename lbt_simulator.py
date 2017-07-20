
import time
import random 
import math 
import logging
import numpy as np 
import matplotlib.pyplot as plt 

## Features
# 1.LBT model
# 2. Packet period model

## TODO
# Add path lost model?
# 

## Configuration
RAND_DELAY = 5000  + random.randint(-4000, 4000)
RETRY_NUM = 5
SAMPLE_TIME = 1000 + random.randint(-100, 100)



logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s') # %(asctime)s 
logging.debug("Debug On")
logging.info("Info On")

class Channel():
    def __init__(self, desc):
        self.nodeList = [] 
        self.desc = desc
        self.occupiedId = None

    def add_node(self, node):
        self.nodeList.append(node)

    def rem_node(self, node):
        self.nodeList.remove(node)

    @property
    def description(self):
        return self.desc 

    def occupy(self, nodeId):
        self.occupiedId = nodeId 

    def release(self, nodeId):
        '''
        Only the node that occupy the channel can release it
        '''
        if self.occupiedId == nodeId:
            self.occupiedId = None 

    def is_busy(self):
        if self.occupiedId is None:
            return False 
        else:
            return True

class Node():
    globalDevList = []
    def __init__(self, devId, periodTicks, occupyTicks, channel):
        if devId in Node.globalDevList:
            raise ValueError("This device id already exists")
        else:
            self.devId = devId
            Node.globalDevList.append(self.devId) 
        self.periodTicks = periodTicks
        self.occupyTicks = occupyTicks
        self.delayTicks = 0
        self.startTicks = 0
        self.channel = channel 
        self.state = "wait"
        self.failCount = 0
        self.successCount = 0
        self.suspendCount = 0
        self.retryCount = 0
        self.randTicks = random.randint(-10000, 10000)


        self.position = (0, 0)

    def start_send(self, globalTicks):
        if self.channel.is_busy() == False:
            logging.debug("Tick {}: Node {} starts to send".format(globalTicks/1000, self.devId))
            self.state = "sending"
            self.startTicks = globalTicks
            self.channel.occupy(self.devId)
            self.successCount += 1
        else:
            logging.debug("Tick {}: Node {} is suspended".format(globalTicks/1000, self.devId))
            self.retryCount += 1
            self.startTicks = globalTicks
            if self.retryCount < RETRY_NUM:
                self.state = "suspend"
                self.suspendCount += 1
                self.delayTicks = RAND_DELAY
            else:
                self.failCount += 1
                self.state = "wait" 

    def end_send(self, globalTicks):
        logging.debug("Tick {}: Node {} ends sending".format(globalTicks/1000, self.devId))
        self.state = "wait"
        self.startTicks = globalTicks
        self.channel.release(self.devId)
    
    def sample(self, globalTicks):
        logging.debug("Tick {}: Node {} starts sampling".format(globalTicks/1000, self.devId))
        self.retryCount = 0
        self.startTicks = globalTicks
        self.state = "sampling"

    def update(self, globalTicks):
        '''
        State machine: (wait) -> (sampling) -> (sending) -> (wait)
                                      |            ^
                                      v            |    
                                  (suspend) ->     |
                                      ^            |
                                      |     <-     v
        '''
        if self.state == "sending":
            if globalTicks - self.startTicks >= self.occupyTicks:
                self.end_send(globalTicks) 
        elif self.state == "wait":
            if globalTicks - self.startTicks >= (self.periodTicks + self.randTicks):
                self.sample(globalTicks)
        elif self.state == "sampling":
            if globalTicks - self.startTicks >= SAMPLE_TIME:
                self.start_send(globalTicks)
        elif self.state == "suspend":
            if globalTicks - self.startTicks >= self.delayTicks:
                self.start_send(globalTicks)

class Counter():
    def __init__(self):
        self.countNum = 0 

    def add(self):
        # time.sleep(0.1)
        # print("{:*^30}".format("counter update"))
        self.countNum += 1
    
    def clear(self):
        self.countNum = 0

    @property
    def ticks(self):
        return self.countNum

class LBT_Model():
    def __init__(self, chList):
        self.counter = Counter()
        self.chList = chList

    def run(self, stopTicks=600000): # 10mins
        while True:
            for c in self.chList:
                for n in c.nodeList:
                    gTicks = self.counter.ticks
                    n.update(gTicks)
            self.counter.add()
            if self.counter.ticks >= stopTicks:
                raise KeyboardInterrupt

class LoRaPacket():
    '''
    All the formulas referred to the sx1276 datasheet
    '''
    def __init__(self, bw="125KHz", sf=7, cr="4/5"):
        if bw == "125KHz":
            self.bw = 125000
        elif bw == "250KHz":
            self.bw = 250000
        elif bw == "500KHz":
            self.bw = 500000
        else:
            raise ValueError("Bandwidth is out of range")

        if sf not in list(range(6, 13)):
            raise ValueError("Value for spread factor is out of range")
        else:
            self.sf = sf
        
        if cr == "4/5":
            self.cr = 1
        elif cr == "4/6":
            self.cr = 2
        elif cr == "4/7":
            self.cr = 3
        elif cr == "4/8":
            self.cr = 4
        else:
            raise ValueError("Value for code rate is out of range")
        self.Tsym = (2**self.sf) / self.bw # Symbol rate 

    def get_time(self, preamble=8, header=1, payload=0, crc=2, ldro=0):
        '''
        payload: 1 to 255
        sf: 6 to 12
        header: 0 or 1, 0 header enable
        crc
        '''
        Tpreamble = (preamble+4.25) * self.Tsym
        temp = math.ceil((8*payload-4*self.sf+28+16*crc-20*header)/(4 * (self.sf-2*ldro)))*(self.cr+4)
        Npl = 8 + max(temp, 0)
        Tpacket = Tpreamble + Npl * self.Tsym
        return Tpacket

class PathLostModel():
    pass 

def plot_hist(lst):
    plt.hist(lst, bins=np.arange(0, lst.max()+2))
    plt.show()

def test(sf, numOfNodes):
    
    t = numOfNodes
    colors = "bgrcmyk"

    for i, s in enumerate(sf):
        packet = LoRaPacket(sf=s)
        tp = int(packet.get_time(payload=255) * 1000) # Tperiod
        result = []
        for j in numOfNodes:
            try:
                ch1 = Channel("Channel 1")
                Node.globalDevList = []
                for k in range(0, j):
                    ch1.add_node(Node(k, 60000, tp, ch1)) # period:60s
                chList = [ch1]
                model = LBT_Model(chList)
                model.run() 
            except KeyboardInterrupt:
                # for c in chList:
                #     for i, n in enumerate(c.nodeList):
                #         logging.info("Node {}: success times {}, fail times {}, suspend times {}".format(i, n.successCount, n.failCount, n.suspendCount))

                fail = np.array([n.failCount for c in chList for n in c.nodeList])
                success = np.array([n.successCount for c in chList for n in c.nodeList])
                suspend = np.array([n.suspendCount for c in chList for n in c.nodeList])

                failMu = np.mean(fail)
                successMu = np.mean(success)
                suspendMu = np.mean(suspend)

                successRate = successMu / (successMu + suspendMu)
                failRate = failMu / (successMu + suspendMu)
                logging.info("Success rate: {}, fail rate: {}".format(successRate, failRate))
                # plot_hist(failList)
                logging.info("Tperiod: {}".format(tp))
                result.append(successRate)
        resultAr = np.array(result)
        plt.plot(t, resultAr, color=colors[i])
        plt.ylim(0, 1.2)

    plt.show()

def main():
    test(range(7,13), range(1, 21))

if __name__ == "__main__":
    main()



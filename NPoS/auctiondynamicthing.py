class auction:
    def __init__(self):
        #Note that ranges are intervals not slices;
        #the lenth 1 range has start=end not end=start+1
        self.ranges = [(start,end) for end in range(4) for start in range(end+1)]
        self.winningbidsonranges=[(None,0) for _ in self.ranges]
    def bid(self,bidid,start,end,amount,verbose=False):
        if verbose:
            print(bidid," bids ",amount," on [",start,",",end,"]")
        #Bid should intersect with all winning bids by same bidder
        for rangeotherbid in [i for i,w in zip(self.ranges,self.winningbidsonranges) if w[0]==bidid]:
            if rangeotherbid[0] > end + 1 or rangeotherbid[1] + 1  < start:
                if verbose:
                    print("Invalid bid as winning on [",rangeotherbid[0],",",rangeotherbid[1],"]")
                return
        rangeindex=self.ranges.index((start,end))
        _,currentwinningbid=self.winningbidsonranges[rangeindex]
        if amount > currentwinningbid:
            self.winningbidsonranges[rangeindex] = (bidid,amount)
    def bestbidonrangeandvalue(self,start,end):
        rangeindex=self.ranges.index((start,end))
        return ((self.winningbidsonranges[rangeindex][0],start,end), self.winningbidsonranges[rangeindex][1]*(end-start+1))
    def calculatewinners(self):
        bestwinnersendingat=[([],0) for _ in range(4)]
        for i in range(4):
            bidderrange,value=self.bestbidonrangeandvalue(0,i)
            bestwinnersendingat[i]=([bidderrange],value)
            for j in range(i):
                bidderrange,value = self.bestbidonrangeandvalue(j+1,i)
                value += bestwinnersendingat[j][1]
                if value > bestwinnersendingat[i][1]:
                    newwinners=bestwinnersendingat[j][0]+[bidderrange]
                    bestwinnersendingat[i]=(newwinners,value)
        return bestwinnersendingat[3]
def example1():
    a=auction()
    a.bid("x",0,3,1,True)
    a.bid("a",0,0,2,True)
    a.bid("a",2,2,53,True)
    a.bid("b",1,1,1,True)
    a.bid("c",2,2,1,True)
    a.bid("d",3,3,1,True)
    print(a.calculatewinners())
    a.bid("x",0,3,2,True)
    print(a.calculatewinners())
    


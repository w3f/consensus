#from itertools import count
import math
class edge:
    def __init__(self,voterid,canid):
        self.voterid=voterid
        self.canid=canid
        #self.index
        #self.voterindex
        #self.canindex


class voter:
    def __init__(self,votetuple):
        self.voterid=votetuple[0]
        self.budget=votetuple[1]
        self.edges=[edge(self.voterid,canid) for canid in votetuple[2]]
        #self.index

class candidate:
    def __init__(self,canid,index):
        self.canid = canid
        self.index=index


import itertools
class assignment:
    def __init__(self,voterlist,candidates, copyassignment=None):
        self.voterlist=voterlist
        self.candidates=candidates
        if copyassignment is None:
            #create edgelist here at cost O(votes size)
            self.edgelist = list(itertools.chain.from_iterable((nom.edges for nom in voterlist)))
            numvoters = len(voterlist)
            numcandidates = len(candidates)
            numedges=len(self.edgelist)
            self.voterload=[0.0 for x in range(numvoters)]
            self.edgeload = [0.0 for x in range(numedges)]
            self.edgeweight = [0.0 for x in range(numedges)]
            self.cansupport=[0.0 for x in range(numcandidates)]
            self.canelected=[False for x in range(numcandidates)]
            self.electedcandidates=set()
            self.canapproval= [0.0 for x in range(numcandidates)]
            #calculate approval here at cost O(numedges)
            for voter in voterlist:
                for edge in voter.edges:
                    self.canapproval[edge.canindex] += voter.budget
            self.canscore = [0.0 for x in range(numcandidates)]
            self.canscorenumerator = [0.0 for x in range(numcandidates)]
            self.canscoredenominator = [0.0 for x in range(numcandidates)]
        else:
            self.edgelist = copyassignment.edgelist
            self.voterload=copyassignment.voterload.copy()
            self.edgeload = copyassignment.edgeload.copy()
            self.edgeweight=copyassignment.edgeweight.copy()
            self.cansupport=copyassignment.cansupport.copy()
            self.canelected=copyassignment.canelected.copy()
            self.electedcandidates=copyassignment.electedcandidates.copy()
            self.canapproval=copyassignment.canapproval.copy()
            self.canscore=copyassignment.canscore.copy()
            self.canscorenumerator = copyassignment.canscorenumerator.copy()
            self.canscoredenominator = copyassignment.canscoredenominator.copy()
    def setload(self, edge,load):
        oldload=self.edgeload[edge.index]
        self.edgeload[edge.index]=load
        self.voterload[edge.voterindex] +=load-oldload
    def setweight(self,edge,weight):
        oldweight=self.edgeweight[edge.index]
        self.edgeweight[edge.index]=weight
        self.cansupport[edge.canindex] +=weight-oldweight
    def setscore(self,candidate,score):
        self.canscore[candidate.index] = score
    def loadstoweights(self):
        for voter in self.voterlist:
            for edge in voter.edges:
                if(self.voterload[voter.index] > 0.0):
                    self.setweight(edge, voter.budget * self.edgeload[edge.index] / self.voterload[voter.index])
    def weightstoloads(self):
        for edge in self.edgelist:
            self.setload(edge, self.edgeweight[edge.index]/self.cansupport[edge.canindex])
    def elect(self,candidate):
        self.canelected[candidate.index]=True
        self.electedcandidates.add(candidate)
    def unelect(self,candidate):
        self.canelected[candidate.index]=False
        self.electedcandidates.remove(candidate)

def setuplists(votelist):
    #Instead of Python's dict here, you can use anything with O(log n) addition and lookup.
    #We can also use a hashmap, by generating a random constant r and useing H(canid+r)
    #since the naive thing is obviously attackable.
    voterlist = [voter(votetuple) for votetuple in votelist]
    candidatedict=dict()
    candidatearray=list()
    numcandidates=0
    numvoters=0
    numedges=0

    #Get an array of candidates that we can reference these by index
    for nom in voterlist:
        nom.index=numvoters
        numvoters+= 1
        for edge in nom.edges:
            edge.index=numedges
            edge.voterindex=nom.index
            numedges += 1
            canid = edge.canid
            if canid in candidatedict:
                edge.candidate=candidatearray[candidatedict[canid]]
                edge.canindex=edge.candidate.index
            else:
                candidatedict[canid]=numcandidates
                newcandidate=candidate(canid,numcandidates)
                candidatearray.append(newcandidate)
                edge.candidate=newcandidate
                edge.canindex=numcandidates
                numcandidates += 1
    return(voterlist,candidatearray)


def seqPhragmén(votelist,numtoelect):
    nomlist,candidates=setuplists(votelist)
    #creating an assignment now also computes the total possible stake for each candidate
    a=assignment(nomlist,candidates)

    for round in range(numtoelect):
        for canindex in range(len(candidates)):
            if not a.canelected[canindex]:
                a.canscore[canindex]=1/a.canapproval[canindex]
        for nom in a.voterlist:
            for edge in nom.edges:
                if not a.canelected[edge.canindex]:
                    a.canscore[edge.canindex] += nom.budget * a.voterload[nom.index] / a.canapproval[edge.canindex]
        bestcandidate=0
        bestscore = 1000 #should be infinite but I'm lazy
        for canindex in range(len(candidates)):
            if not a.canelected[canindex] and a.canscore[canindex] < bestscore:
                bestscore=a.canscore[canindex]
                bestcandidate=canindex
        electedcandidate=candidates[bestcandidate]
        a.canelected[bestcandidate]=True
        #electedcandidate.electedpos=round
        a.elect(electedcandidate)
        for nom in a.voterlist:
            for edge in nom.edges:
                if edge.canindex == bestcandidate:
                    a.setload(edge,a.canscore[bestcandidate]-a.voterload[nom.index])
    a.loadstoweights()
    return a

def calculateScores(a,cutoff):
    for canindex in range(len(a.candidates)):
        if not a.canelected[canindex]:
            a.canscorenumerator[canindex]=0
            a.canscoredenominator[canindex]=1
    for nom in a.voterlist:
        numeratorcontrib=nom.budget
        denominatorcontrib=0
        for edge in nom.edges:
            if a.canelected[edge.canindex]:
                if a.cansupport[edge.canindex] > cutoff:
                    denominatorcontrib += a.edgeweight[edge.index]/a.cansupport[edge.canindex]
                else:
                    numeratorcontrib -= a.edgeweight[edge.index]
        for edge in nom.edges:
            if not a.canelected[edge.canindex]:
                a.canscorenumerator[edge.canindex] +=numeratorcontrib
                a.canscoredenominator[edge.canindex] +=denominatorcontrib
    for canindex in range(len(a.candidates)):
        if not a.canelected[canindex]:
           a.canscore[canindex] = a.canscorenumerator[canindex]/a.canscoredenominator[canindex]
    #for canindex in range(len(a.candidates)):
        #if not a.canelected[canindex]:
            #print(a.candidates[canindex].canid," has score ", a.canscore[canindex]," with cutoff ",cutoff)
            #print("Approval stake: ", a.canapproval[canindex]," support: ",a.cansupport[canindex]," denominator: ",a.canscoredenominator[canindex], " numerator: ",a.canscorenumerator[canindex])


def calculateMaxScore(a):
    supportList=[a.cansupport[can.index] for can in a.electedcandidates]
    supportList.append(0.0)
    supportList.sort()
    lowerindex=0
    upperindex=len(a.electedcandidates)+1
    currentindex=0
    while(True):
        #print(len(supportList), currentindex, len(a.electedcandidates),upperindex,lowerindex)
        cutoff=supportList[currentindex]
        calculateScores(a,cutoff)
        scores=[(can, a.canscore[can.index]) for can in a.candidates if not a.canelected[can.index]]
        bestcandidate,score=max(scores,key=lambda x: x[1])
        if score > cutoff:
            # In this case both score and cutoff are lower bounds to the max score
            lowerindex=len([s for s in supportList if s <= score]) - 1
            #print("lowerindex ",lowerindex, " upperindex ",upperindex, " cutoff ", cutoff, "score ",score, " candidate ",bestcandidate.canid)
            #print("bottom support ",supportList[0], " real lowest support ",supportList[1], " highest support ",supportList[-1])
            if currentindex == upperindex-1 or currentindex==lowerindex:
                return bestcandidate,score
        elif score < cutoff:
            # In this case, cutoff is an upper bounf for the max score
            upperindex=currentindex
        else:
            # If they are magically equal, this is the score
            return bestcandidate,score
        currentindex=(lowerindex + upperindex) // 2

def insertWithScore(a,candidate,cutoff):
    oldcansupport=a.cansupport.copy()
    a.elect(candidate)
    for nom in a.voterlist:
        for newedge in nom.edges:
            if newedge.canindex== candidate.index:
                usedbudget = sum([a.edgeweight[edge.index] for edge in nom.edges])
                a.setweight(newedge, nom.budget-usedbudget)
                for edge in nom.edges:
                    if edge.canindex != candidate.index and a.edgeweight[edge.index] > 0.0:
                        if oldcansupport[edge.canindex] > cutoff:
                            fractiontotake = cutoff / oldcansupport[edge.canindex]
                            a.setweight(newedge, a.edgeweight[newedge.index] + a.edgeweight[edge.index]* fractiontotake)
                            a.setweight(edge, a.edgeweight[edge.index] * (1-fractiontotake))

def approvalvoting(votelist,numtoelect):
    nomlist,candidates=setuplists(votelist)
    #creating an assignment now also computes the total possible stake for each candidate
    a=assignment(nomlist,candidates)

    candidatessorted=sorted(candidates, key = lambda x : a.canapproval[x.index], reverse=True)
    for candidate in candidatessorted[0:numtoelect]:
        a.elect(candidate)
    for nom in a.voterlist:
        numbelected=len([edge for edge in nom.edges if a.canelected[edge.canindex]])
        if (numbelected > 0):
            for edge in nom.edges:
                a.setweight(edge,nom.budget/numbelected)
    return a

def printresult(a,listvoters=True,listelectedcandidates=True):
    if listelectedcandidates:
        for candidate in a.electedcandidates:
            print(candidate.canid," is elected with stake ",a.cansupport[candidate.index], "and score ",a.canscore[candidate.index])
        print()
    if listvoters:
        for nom in a.voterlist:
            print(nom.voterid," has load ",a.voterload[nom.index], "and supported ")
            for edge in nom.edges:
                print(edge.canid," with stake ",a.edgeweight[edge.index], end=" ")
            print()
    print("Minimum support ",min([a.cansupport[candidate.index] for candidate in a.electedcandidates]))

def equalise(a, nom, tolerance):
    # Attempts to redistribute the nominators budget between elected validators
    # Assumes that all elected validators have backedstake set correctly
    # returns the max difference in stakes between sup

    electededges=[edge for edge in nom.edges if a.canelected[edge.canindex]]
    if len(electededges)==0:
        return 0.0
    stakeused = sum([a.edgeweight[edge.index] for edge in electededges])
    backedstakes=[a.cansupport[edge.canindex] for edge in electededges]
    backingbackedstakes=[a.cansupport[edge.canindex] for edge in electededges if a.edgeweight[edge.index] > 0.0]
    if len(backingbackedstakes) > 0:
        difference = max(backingbackedstakes)-min(backedstakes)
        difference += nom.budget-stakeused
        if difference < tolerance:
            return difference
    else:
        difference = nom.budget
    #remove all backing
    for edge in nom.edges:
        a.setweight(edge, 0.0)
    electededges.sort(key=lambda x: a.cansupport[x.canindex])
    cumulativebackedstake=0
    lastcandidateindex=len(electededges)-1
    for i in range(len(electededges)):
        backedstake=a.cansupport[electededges[i].canindex]
        #print(nom.nomid,electededges[i].valiid,backedstake,cumulativebackedstake,i)
        if backedstake * i - cumulativebackedstake > nom.budget:
            lastcandidateindex=i-1
            break
        cumulativebackedstake +=backedstake
    laststake=a.cansupport[electededges[lastcandidateindex].canindex]
    waystosplit=lastcandidateindex+1
    excess = nom.budget + cumulativebackedstake -  laststake*waystosplit
    for edge in electededges[0:waystosplit]:
        a.setweight(edge,excess / waystosplit + laststake - a.cansupport[edge.canindex])
    return difference

import random
def equaliseall(a,maxiterations,tolerance,debug=False):
    for i in range(maxiterations):
        for j in range(len(a.voterlist)):
            nom=random.choice(a.voterlist)
            equalise(a,nom,tolerance/10)
        maxdifference=0
        for nom in a.voterlist:
            difference=equalise(a,nom,tolerance/10)
            maxdifference=max(difference,maxdifference)
        if maxdifference < tolerance:
            if debug:
                print("max iterations ",maxiterations," actual iterations ",i+1)
            return
    if maxiterations > 1 or debug:
        print(" reached max iterations ",maxiterations)

def seqPhragménwithpostprocessing(votelist,numtoelect, ratio=1):
    a = seqPhragmén(votelist,numtoelect)
    passes=math.floor(ratio*numtoelect)
    equaliseall(a,ratio*numtoelect,0.1, True)
    return a


def factor3point15(votelist, numtoelect,tolerance=0.1):
    nomlist,candidates=setuplists(votelist)
    a=assignment(nomlist,candidates)

    for round in range(numtoelect):
        bestcandidate,score=calculateMaxScore(a)
        insertWithScore(a,bestcandidate, score)
        equaliseall(a,1000000,tolerance)
    return a

def maybecandidate(a,newcandidate,shouldremoveworst, tolerance):
    assert(a.canelected[newcandidate.index]==False)
    currentvalue=min([a.cansupport[candidate.index] for candidate in a.electedcandidates])
    #To find a new assignment without losing our current one, we will need to copy the edges
    b=assignment(a.voterlist,a.candidates,a)
    if shouldremoveworst:
        worstcanidate =min(electedcandidates, key = lambda x: b.cansupport[x.index])
        b.unelect(worstcandidate)
    b.elect(newcandidate)
    equaliseall(b,100000000,tolerance)
    newvalue=min([b.cansupport[candidate.index] for candidate in b.electedcandidates])
    return b, newvalue

def SFFB18(votelist, numtoelect,tolerance=0.1):
    nomlist,candidates=setuplists(votelist)
    a=assignment(nomlist,candidates)
    for round in range(numtoelect):
        if round == 0:
            newcandidate=max([(can,a.canapproval[can.index]) for can in a.candidates],key = lambda x : x[1])[0]
            a.elect(newcandidate)
            equaliseall(a,1,tolerance)
        else:
            bestvalue=0
            for can in a.candidates:
                if not a.canelected[can.index] and a.canapproval[can.index] > bestvalue:
                    b,newvalue = maybecandidate(a,can, False, tolerance)
                    if newvalue > bestvalue:
                        bestassignment=b
                        bestvalue=newvalue
            if bestvalue > 0:
                a=bestassignment
    return a

def binarysearchfeasible(votelist,numtoelect,tolerance=0.1):
    nomlist,candidates=setuplists(votelist)
    a=assignment(nomlist,candidates)

    #First do factor 3.15
    #but keep track of the order we elect people and the value then
    orderelectedwithvalue=[]
    for round in range(numtoelect):
        bestcandidate,score=calculateMaxScore(a)
        insertWithScore(a,bestcandidate, score)
        equaliseall(a,1000000,tolerance/numtoelect)
        currentvalue=min([a.cansupport[candidate.index] for candidate in a.electedcandidates])
        orderelectedwithvalue.append((bestcandidate,currentvalue))
    if len(a.candidates)==numtoelect:
        return a
    bestknownvalue=currentvalue
    bestassignment=assignment(a.voterlist,a.candidates,a)
    bestorderelected=orderelectedwithvalue.copy()
    maxunelectedapproval = max([a.canapproval[i] for i in range(len(a.candidates)) if not a.canelected[i]])
    totalvotes=sum([nom.budget for nom in a.voterlist])
    maxvalue=min(3.15*currentvalue, max(currentvalue,maxunelectedapproval), totalvotes/numtoelect)
    while(maxvalue - bestknownvalue > tolerance):
        targetvalue=math.sqrt(maxvalue*bestknownvalue)
        lastgoodindex=len([x for x in orderelectedwithvalue if x[1] >= targetvalue])-1
        #print(orderelectedwithvalue, targetvalue,lastgoodindex, maxvalue,bestknownvalue,currentvalue,targetvalue)
        assert(lastgoodindex >= 0)
        assert(orderelectedwithvalue[lastgoodindex][1] >= targetvalue)
        for x in orderelectedwithvalue[lastgoodindex+1:]:
            a.unelect(x[0])
        del orderelectedwithvalue[lastgoodindex+1:]
        for nom in a.voterlist:
            for edge in nom.edges:
                if not a.canelected[edge.canindex]:
                    a.setweight(edge,0)
        equaliseall(a,1000000,tolerance/numtoelect)
        currentvalue=min([a.cansupport[candidate.index] for candidate in a.electedcandidates])
        if currentvalue < targetvalue:
            if targetvalue >= sqrt(currentvalue, maxvalue):
                #At this point we are getting so much error from tolerance in equaliseall
                #that we should give up
                print("Giving up with error at most ",maxvalue-bestknownvalue)
                return
            else:
                targetvalue=currentvalue
        #print(targetvalue,lastgoodindex, maxvalue,bestknownvalue,currentvalue)


        for round in range(lastgoodindex+1,numtoelect):
            # First try maxscore candidate, which will help with PJR
            bestcandidate,score=calculateMaxScore(a)
            if score >= targetvalue:
                insertWithScore(a,bestcandidate, score)
                equaliseall(a,1000000,tolerance/numtoelect)
                currentvalue=min([a.cansupport[candidate.index] for candidate in a.electedcandidates])
                assert(currentvalue >= targetvalue)
                orderelectedwithvalue.append((bestcandidate,currentvalue))
                continue
            else:
                b,newvalue = maybecandidate(a,bestcandidate, False, tolerance)
                if newvalue >= targetvalue:
                    a=b
                    orderelectedwithvalue.append((bestcandidate,newvalue))
                    currentvalue=newvalue
                    continue
            #Then try some candidates in which we are guaranteed that one is feasible if threshold >= d*/2
            calculateScores(a,targetvalue/2)
            scores=[(can, a.canscore[can.index]) for can in a.candidates if not a.canelected[can.index] and a.canapproval[can.index] >= targetvalue and a.canscore[can.index] >= targetvalue/2]
            scores.sort(reverse=True,key=lambda x: x[1])
            for can,score in scores:
                b,newvalue = maybecandidate(a,can, False, tolerance)
                if newvalue >= targetvalue:
                    a=b
                    orderelectedwithvalue.append((can,newvalue))
                    currentvalue=newvalue
                    break
            else:
                break
        # print("here",currentvalue,targetvalue)
        if len(a.electedcandidates) < numtoelect:
            maxvalue = targetvalue
            a=bestassignment
            orderelectedwithvalue=bestorderelected
        else:
            bestknownvalue=currentvalue
            bestassignment=assignment(a.voterlist,a.candidates,a)
            bestorderelected=orderelectedwithvalue.copy()
    return a

import unittest
class electiontests(unittest.TestCase):
    def testexample1Phragmén(self):
        votelist=[("A",10.0,["X","Y"]),("B",20.0,["X","Z"]),("C",30.0,["Y","Z"])]
        a = seqPhragmén(votelist,2)
        self.assertEqual({can.canid for can in a.electedcandidates},{"Y","Z"})
        self.assertAlmostEqual(a.canscore[2],0.02)
        self.assertAlmostEqual(a.canscore[1],0.04)
    def testexample1approval(self):
        votelist=[("A",10.0,["X","Y"]),("B",20.0,["X","Z"]),("C",30.0,["Y","Z"])]
        a = approvalvoting(votelist,2)
        self.assertEqual({can.canid for can in a.electedcandidates},{"Y","Z"})
        self.assertAlmostEqual(a.canapproval[2],50.0)
        self.assertAlmostEqual(a.canapproval[1],40.0)
def dotests():
    unittest.main()

import time
def doall(votelist, numtoelect, listvoters=True, listcans=True):
    if listvoters:
        print("Votes ",votelist)
    alglist=[(approvalvoting,"Approval voting"), (seqPhragmén, "Sequential Phragmén"),
             (seqPhragménwithpostprocessing, "Sequential Phragmén with post processing"),
             (factor3point15, "The factor 3.15 thing"), (binarysearchfeasible,"Factor 2 by binary search"), (SFFB18, "SFFB18")]
    for alg,name in alglist:
        st=time.perf_counter()
        a = alg(votelist,numtoelect)
        et=time.perf_counter()
        print(name, " gives")
        printresult(a,listvoters,listcans)
        print(" in ",et-st," seconds.")
        print()


def example1():
    votelist=[("A",10.0,["X","Y"]),("B",20.0,["X","Z"]),("C",30.0,["Y","Z"])]
    doall(votelist,2)


def example2():
    # Approval voting does not do so well for this kind of thing.
    votelist=[("A",30.0,["T", "U","V","W"]),("B",20.0,["X"]),("C",20.0,["Y"]),("D",20.0,["Z"])]
    doall(votelist,4)

def example3():
    #Proportional representation test.
    #Red should has 50% more votes than blue. So under PR, it would get 12/20 seats
    redparty=["Red"+str(i) for i in range(20)]
    blueparty=["Blue"+str(i) for i in range(20)]
    redvoters = [("RedV"+str(i),20.0,redparty) for i in range(30)]
    bluevoters = [("BlueV"+str(i),20.0,blueparty) for i in range(20)]
    votelist= redvoters+bluevoters
    doall(votelist, 20, False)


def example4():
    #Now we want an example where seq Phragmén is not so good.
    votelist=[("A",30.0,["V","W"]),("B",20.0,["V","Y"]),("C",20.0,["W","Z"]),("D",20.0,["Z"])]
    print("Votes ",votelist)
    doall(votelist,4)

def example5():
    votelist = [
		("10", 1000, ["10"]),
		("20", 1000, ["20"]),
		("30", 1000, ["30"]),
		("40", 1000, ["40"]),
		('2', 500, ['10', '20', '30']),
		('4', 500, ['10', '20', '40'])
	]
    print("Votes ",votelist)
    doall(votelist,4)

def example6():
    #Now we want an example where seq Phragmén is not so good.
    votelist=[("A",100.0,["V","W","X","Y","Z"]),("B",100.0,["W","X","Y","Z"]),
              ("C",100.0,["X","Y","Z"]),("D",100.0,["Y","Z"]), ("E",100.0,["Z"]),
              ("M",50.0, ["M"])]
    print("Votes ",votelist)
    doall(votelist,5)

def exampleLine():
    votelist = [
		("a", 2000, ["A"]),
		("b", 1000, ["A","B"]),
		("c", 1000, ["B","C"]),
		("d", 1000, ["C","D"]),
		("e", 1000, ["D","E"]),
		("f", 1000, ["E","F"]),
                ("g", 1000, ["F","G"])
	]
    doall(votelist,7)

def ri(vals=20,noms=2000, votesize=10):
    #Let's try a random instance
    candidates=["Val"+str(i) for i in range(vals)]
    votelist=[("Nom"+str(i), 100, random.sample(candidates,votesize)) for i in range(noms)]
    doall(votelist, vals // 2, False, False)

def ripartylist(vals=200,noms=2000, votesize=10,seed=1):
    #Half the validators are in a party which 1/4 of the nominators vote for.
    # Approval voting does worse now
    # and this is probably more realistic than the pure random instance.
    random.seed(seed)
    candidates=["Val"+str(i) for i in range(vals//2)]
    partycandidates=["PartyVal"+str(i) for i in range(vals- vals // 2)]
    partynoms = noms // 4
    votelist=[("Nom"+str(i), 100, random.sample(candidates,votesize)) for i in range(noms - partynoms)]
    votelist += [("Nom"+str(i), 100, partycandidates) for i in range(partynoms)]
    return votelist


def riparty(vals=200,noms=2000, votesize=10,seed=1):
    #Half the validators are in a party which 1/4 of the nominators vote for.
    # Approval voting does worse now
    # and this is probably more realistic than the pure random instance.
    votelist=ripartylist(vals,noms,votesize,seed)
    doall(votelist, vals // 4, False, False)






























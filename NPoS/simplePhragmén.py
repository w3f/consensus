#from itertools import count
class edge:
    def __init__(self,nomid,valiid):
        self.nomid=nomid
        self.valiid=valiid
        #self.validator
        self.load=0
        self.weight=0

class nominator:
    def __init__(self,votetuple):
        self.nomid=votetuple[0]
        self.budget=votetuple[1]
        self.edges=[edge(self.nomid,valiid) for valiid in votetuple[2]]
        self.load=0

class candidate:
    def __init__(self,valiid,valindex):
        self.valiid = valiid
        self.valindex=valindex
        self.approvalstake=0
        self.elected=False
        self.backedstake=0
        self.score=0
        self.scoredenom=0

def setuplists(votelist):
    #Instead of Python's dict here, you can use anything with O(log n) addition and lookup.
    #We can also use a hashmap like dict, by generating a random constant r and useing H(canid+r)
    #since the naive thing is obviously attackable.
    nomlist = [nominator(votetuple) for votetuple in votelist]
    candidatedict=dict()
    candidatearray=list()
    numcandidates=0
    #Get an array of candidates. ]#We could reference these by index
    #rather than pointer
    for nom in nomlist:
        for edge in nom.edges:
            valiid = edge.valiid
            if valiid in candidatedict:
                edge.candidate=candidatearray[candidatedict[valiid]]
            else:
                candidatedict[valiid]=numcandidates
                newcandidate=candidate(valiid,numcandidates)
                candidatearray.append(newcandidate)
                edge.candidate=newcandidate
                numcandidates += 1
    return(nomlist,candidatearray)
    

def seqPhragmén(votelist,numtoelect):
    nomlist,candidates=setuplists(votelist)
    #Compute the total possible stake for each candidate
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approvalstake += nom.budget
        
    electedcandidates=list()
    for round in range(numtoelect):
        for candidate in candidates:
            if not candidate.elected:
                candidate.score=1/candidate.approvalstake
        for nom in nomlist:
            for edge in nom.edges:
                if not edge.candidate.elected:
                    edge.candidate.score +=nom.budget * nom.load / edge.candidate.approvalstake
        bestcandidate=0
        bestscore = 1000 #should be infinite but I'm lazy
        for candidate in candidates:
            if not candidate.elected and candidate.score < bestscore:
                bestscore=candidate.score
                bestcandidate=candidate.valindex
        electedcandidate=candidates[bestcandidate]
        electedcandidate.elected=True
        electedcandidate.electedpos=round
        electedcandidates.append(electedcandidate)
        for nom in nomlist:
            for edge in nom.edges:
                if edge.candidate.valindex == bestcandidate:
                    edge.load=electedcandidate.score - nom.load
                    nom.load=electedcandidate.score

    for candidate in electedcandidates:
        candidate.backedstake=0

    for nom in nomlist:
            for edge in nom.edges:
                if nom.load > 0.0:
                    edge.weight = nom.budget * edge.load/nom.load
                    edge.candidate.backedstake += edge.weight
                else:
                    edge.weight = 0
    return (nomlist,electedcandidates)

def calculateMaxScoreNoCutoff(nomlist,candidates):
    # First we compute the denominator of the score
    for candidate in candidates:
        if not candidate.elected:
            candidate.scoredenom=1.0
    for nom in nomlist:
        denominatorcontrib = 0
        for edge in nom.edges:
             if edge.candidate.elected:
                denominatorcontrib += edge.weight/edge.candidate.backedstake
        # print(nom.nomid, denominatorcontrib)
        for edge in nom.edges:
            if not edge.candidate.elected:
               edge.candidate.scoredenom += denominatorcontrib
               # print(edge.candidate.valiid, nom.nomid, denominatorcontrib, edge.candidate.scoredenom) 
    # Then we divide. Not that score here is comparable to the recipricol of the score in seqPhragmen.
    # In particular there low scores are good whereas here high scores are good.
    bestcandidate=0
    bestscore = 0.0
    for candidate in candidates:
        print(candidate.valiid, candidate.approvalstake, candidate.scoredenom)
        if candidate.approvalstake > 0.0:
            candidate.score = candidate.approvalstake/candidate.scoredenom
            if not candidate.elected and candidate.score > bestscore:
                bestscore=candidate.score
                bestcandidate=candidate
        else:
            candidate.score=0.0
    # print(len(candidates), bestcandidate, bestscore)
    return (bestcandidate,bestscore)

def electWithScore(nomlist, electedcandidate, cutoff):
    for nom in nomlist:
        for newedge in nom.edges:
            if newedge.valiid == electedcandidate.valiid:
                usedbudget = sum([edge.weight for edge in nom.edges])
                newedge.weight = nom.budget-usedbudget
                electedcandidate.backedstake += nom.budget-usedbudget
                for edge in nom.edges:
                    if edge.valiid != electedcandidate.valiid and edge.weight > 0.0:
                        if edge.candidate.backedstake > cutoff:
                            staketotake = edge.weight * cutoff / edge.candidate.backedstake
                            newedge.weight += staketotake
                            edge.weight -= staketotake
                            edge.candidate.backedstake -= staketotake
                            electedcandidate.backedstake += staketotake


def approvalvoting(votelist,numtoelect):
    nomlist,candidates=setuplists(votelist)
    #Compute the total possible stake for each candidate
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approvalstake += nom.budget
            edge.weight = nom.budget/min(len(nom.edges),numtoelect)
            edge.candidate.backedstake += edge.weight
    candidates.sort( key = lambda x : x.approvalstake, reverse=True)
    electedcandidates=candidates[0:numtoelect]
    return nomlist,electedcandidates

def printresult(nomlist,electedcandidates):
    for candidate in electedcandidates:
        print(candidate.valiid," is elected with stake ",candidate.backedstake, "and score ",candidate.score)
    print()
    for nom in nomlist:
        print(nom.nomid," has load ",nom.load, "and supported ")
        for edge in nom.edges:
            print(edge.valiid," with stake ",edge.weight, end=" ")
        print()

def equalise(nom, tolerance):
    # Attempts to redistribute the nominators budget between elected validators
    # Assumes that all elected validators have backedstake set correctly
    # returns the max difference in stakes between sup
    
    electededges=[edge for edge in nom.edges if edge.candidate.elected]
    if len(electededges)==0:
        return 0.0
    stakeused = sum([edge.weight for edge in electededges])
    backedstakes=[edge.candidate.backedstake for edge in electededges]
    backingbackedstakes=[edge.candidate.backedstake for edge in electededges if edge.weight > 0.0]
    if len(backingbackedstakes) > 0:
        difference = max(backingbackedstakes)-min(backedstakes)
        difference += nom.budget-stakeused
        if difference < tolerance:
            return difference
    else:
        difference = nom.budget
    #remove all backing
    for edge in nom.edges:
        edge.candidate.backedstake -= edge.weight
        edge.weight=0
    electededges.sort(key=lambda x: x.candidate.backedstake)
    cumulativebackedstake=0
    lastcandidateindex=len(electededges)-1
    for i in range(len(electededges)):
        backedstake=electededges[i].candidate.backedstake
        #print(nom.nomid,electededges[i].valiid,backedstake,cumulativebackedstake,i)
        if backedstake * i - cumulativebackedstake > nom.budget:
            lastcandidateindex=i-1
            break
        cumulativebackedstake +=backedstake
    laststake=electededges[lastcandidateindex].candidate.backedstake
    waystosplit=lastcandidateindex+1
    excess = nom.budget + cumulativebackedstake -  laststake*waystosplit
    for edge in electededges[0:waystosplit]:
        edge.weight = excess / waystosplit + laststake - edge.candidate.backedstake
        edge.candidate.backedstake += edge.weight
    return difference

import random
def equaliseall(nomlist,maxiterations,tolerance):
    for i in range(maxiterations):
        for j in range(len(nomlist)):
            nom=random.choice(nomlist)
            equalise(nom,tolerance/10)
        maxdifference=0
        for nom in nomlist:
            difference=equalise(nom,tolerance/10)
            maxdifference=max(difference,maxdifference)
        if maxdifference < tolerance:
            return

def seqPhragménwithpostprocessing(votelist,numtoelect):
    nomlist,electedcandidates = seqPhragmén(votelist,numtoelect)
    equaliseall(nomlist,2,0.1)
    return nomlist,electedcandidates

def factor3point15(votelist, numtoelect,tolerance=0.1):
    nomlist,candidates=setuplists(votelist)
    # Compute the total possible stake for each candidate
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approvalstake += nom.budget
        
    electedcandidates=list()
    for round in range(numtoelect):
        electedcandidate,score=calculateMaxScoreNoCutoff(nomlist,candidates)
        electWithScore(nomlist, electedcandidate, score)
        electedcandidate.elected=True
        electedcandidates.append(electedcandidate)
        electedcandidate.electedpos=round
        equaliseall(nomlist,100,tolerance)
    return nomlist,electedcandidates

def example1():
    votelist=[("A",10.0,["X","Y"]),("B",20.0,["X","Z"]),("C",30.0,["Y","Z"])]
    print("Votes ",votelist)
    nomlist, electedcandidates = seqPhragmén(votelist,2)
    print("Sequential Phragmén gives")
    printresult(nomlist, electedcandidates)
    nomlist, electedcandidates = approvalvoting(votelist,2)
    print()
    print("Approval voting gives")
    printresult(nomlist, electedcandidates)
    nomlist, electedcandidates = seqPhragménwithpostprocessing(votelist,2)
    print("Sequential Phragmén with post processing gives")
    printresult(nomlist, electedcandidates)
    nomlist, electedcandidates = factor3point15(votelist,2)
    print("Factor 3.15 thing gives")
    printresult(nomlist, electedcandidates)

def example2():
    votelist = [
		("10", 1000, ["10"]),
		("20", 1000, ["20"]),
		("30", 1000, ["30"]),
		("40", 1000, ["40"]),
		('2', 500, ['10', '20', '30']),
		('4', 500, ['10', '20', '40'])
	]
    print("Votes ",votelist)
    nomlist, electedcandidates = seqPhragmén(votelist,2)
    print("Sequential Phragmén gives")
    printresult(nomlist, electedcandidates)
    nomlist, electedcandidates = approvalvoting(votelist,2)
    print()
    print("Approval voting gives")
    printresult(nomlist, electedcandidates)
    nomlist, electedcandidates = seqPhragménwithpostprocessing(votelist,2)
    print("Sequential Phragmén with post processing gives")
    printresult(nomlist, electedcandidates)
    nomlist, electedcandidates = factor3point15(votelist,2)
    print("Factor 3.15 thing gives")
    printresult(nomlist, electedcandidates)

import unittest
class electiontests(unittest.TestCase):
    def testexample1Phragmén(self):
        votelist=[("A",10.0,["X","Y"]),("B",20.0,["X","Z"]),("C",30.0,["Y","Z"])]
        nomlist, electedcandidates = seqPhragmén(votelist,2)
        self.assertEqual(electedcandidates[0].valiid,"Z")
        self.assertAlmostEqual(electedcandidates[0].score,0.02)
        self.assertEqual(electedcandidates[1].valiid,"Y")
        self.assertAlmostEqual(electedcandidates[1].score,0.04)
    def testexample1approval(self):
        votelist=[("A",10.0,["X","Y"]),("B",20.0,["X","Z"]),("C",30.0,["Y","Z"])]
        nomlist, electedcandidates = approvalvoting(votelist,2)
        self.assertEqual(electedcandidates[0].valiid,"Z")
        self.assertAlmostEqual(electedcandidates[0].approvalstake,50.0)
        self.assertEqual(electedcandidates[1].valiid,"Y")
        self.assertAlmostEqual(electedcandidates[1].approvalstake,40.0)
def dotests():
    unittest.main()
    
    


    
    
            

    


    
            

    
        
        
        
            
            

                
        


            
    
    
    
    
    

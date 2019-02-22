import unittest
import math
import sys
import random


class edge:
    def __init__(self, nomid, valiid):
        self.nomid = nomid
        self.valiid = valiid
        self.load = 0


class nominator:
    def __init__(self, votetuple):
        self.nomid = votetuple[0]
        self.budget = votetuple[1]
        self.edges = [edge(self.nomid, valiid) for valiid in votetuple[2]]
        self.load = 0


class candidate:
    def __init__(self, valiid, valindex):
        self.valiid = valiid
        self.valindex = valindex
        self.approvalstake = 0
        self.elected = False
        self.backedstake = 0
        self.score = 0


def setup_lists(votelist):
    '''
    Instead of Python's dict here, you can use anything with O(log n)
    addition and lookup.We can also use a hashmap like dict, by generating
    a random constant r and useing H(canid+r)
    since the naive thing is obviously attackable.
    '''
    nomlist = [nominator(votetuple) for votetuple in votelist]
    candidatedict = dict()
    candidatearray = list()
    numcandidates = 0

    # Get an array of candidates. ]#We could reference these by index
    # rather than pointer

    for nom in nomlist:
        for edge in nom.edges:
            valiid = edge.valiid
            if valiid in candidatedict:
                edge.candidate = candidatearray[candidatedict[valiid]]
            else:
                candidatedict[valiid] = numcandidates
                newcandidate = candidate(valiid, numcandidates)
                candidatearray.append(newcandidate)
                edge.candidate = newcandidate
                numcandidates += 1
    return(nomlist, candidatearray)


def seq_phragmén(votelist, numtoelect):
    nomlist, candidates = setup_lists(votelist)
    # Compute the total possible stake for each candidate
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approvalstake += nom.budget

    electedcandidates = list()
    for round in range(numtoelect):
        for candidate in candidates:
            if not candidate.elected:
                candidate.score = 1/candidate.approvalstake
        for nom in nomlist:
            for edge in nom.edges:
                if not edge.candidate.elected:
                    edge.candidate.score += nom.budget * nom.load / edge.candidate.approvalstake

        bestcandidate = 0
        bestscore = math.inf

        for candidate in candidates:
            if not candidate.elected and candidate.score < bestscore:
                bestscore = candidate.score
                bestcandidate = candidate.valindex

        electedcandidate = candidates[bestcandidate]
        electedcandidate.elected = True
        electedcandidate.electedpos = round
        electedcandidates.append(electedcandidate)

        for nom in nomlist:
            for edge in nom.edges:
                if edge.candidate.valindex == bestcandidate:
                    edge.load = electedcandidate.score - nom.load
                    nom.load = electedcandidate.score

    for candidate in electedcandidates:
        candidate.backedstake = 0

    for nom in nomlist:
        for edge in nom.edges:
            edge.backingstake = nom.budget * edge.load/nom.load
            edge.candidate.backedstake += edge.backingstake
    return nomlist, electedcandidates


def approval_voting(votelist, numtoelect):
    nomlist, candidates = setup_lists(votelist)

    # Compute the total possible stake for each candidate
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approvalstake += nom.budget
            edge.backingstake = nom.budget/min(len(nom.edges), numtoelect)
            edge.candidate.backedstake += edge.backingstake

    candidates.sort(key=lambda x: x.approvalstake, reverse=True)

    electedcandidates = candidates[0:numtoelect]
    return nomlist, electedcandidates


def print_result(nomlist, electedcandidates):
    for candidate in electedcandidates:
        print(candidate.valiid, " is elected with stake ", candidate.backedstake, "and score ", candidate.score)
    
    print()
    for nom in nomlist:
        print(nom.nomid, " has load ", nom.load, "and supported ")
        for edge in nom.edges:
            print(edge.valiid, " with stake ", edge.backingstake, end=" ")
        print()


def equalise(nom, tolerance):
    # Attempts to redistribute the nominators budget between elected validators
    # Assumes that all elected validators have backedstake set correctly
    # returns the max difference in stakes between sup
    
    electededges = [edge for edge in nom.edges if edge.candidate.elected]
    if len(electededges) == 0:
        return 0.0
    stakeused = sum([edge.backingstake for edge in electededges])
    backedstakes = [edge.candidate.backedstake for edge in electededges]
    backingbackedstakes = [edge.candidate.backedstake for edge in electededges if edge.backingstake > 0.0]
    if len(backingbackedstakes) > 0:
        difference = max(backingbackedstakes)-min(backedstakes)
        difference += nom.budget-stakeused
        if difference < tolerance:
            return difference
    else:
        difference = nom.budget

    # remove all backing
    for edge in nom.edges:
        edge.candidate.backedstake -= edge.backingstake
        edge.backingstake = 0

    electededges.sort(key=lambda x: x.candidate.backedstake)
    cumulativebackedstake = 0
    lastcandidateindex = len(electededges)-1

    for i in range(len(electededges)):
        backedstake = electededges[i].candidate.backedstake
        if backedstake * i - cumulativebackedstake > nom.budget:
            lastcandidateindex = i-1
            break
        cumulativebackedstake += backedstake

    laststake = electededges[lastcandidateindex].candidate.backedstake
    waystosplit = lastcandidateindex+1
    excess = nom.budget + cumulativebackedstake - laststake*waystosplit
    for edge in electededges[0:waystosplit]:
        edge.backingstake = excess / waystosplit + laststake - edge.candidate.backedstake
        edge.candidate.backedstake += edge.backingstake
    return difference


def equalise_all(nomlist, maxiterations, tolerance):
    for i in range(maxiterations):
        for j in range(len(nomlist)):
            nom = random.choice(nomlist)
            equalise(nom, tolerance/10)
        maxdifference = 0
        for nom in nomlist:
            difference = equalise(nom, tolerance/10)
            maxdifference = max(difference, maxdifference)
        if maxdifference < tolerance:
            return


def seq_phragmén_with_postprocessing(votelist, numtoelect):
    nomlist, electedcandidates = seq_phragmén(votelist, numtoelect)
    equalise_all(nomlist, 2, 0.1)
    return nomlist, electedcandidates    


def example1():
    votelist = [
        ("A", 10.0, ["X", "Y"]),
        ("B", 20.0, ["X", "Z"]),
        ("C", 30.0, ["Y", "Z"])]
    print("Votes ", votelist)
    nomlist, electedcandidates = seq_phragmén(votelist, 2)
    print("Sequential Phragmén gives")
    print_result(nomlist, electedcandidates)
    nomlist, electedcandidates = approval_voting(votelist, 2)
    print()
    print("Approval voting gives")
    print_result(nomlist, electedcandidates)
    nomlist, electedcandidates = seq_phragmén_with_postprocessing(votelist, 2)
    print("Sequential Phragmén with post processing gives")
    print_result(nomlist, electedcandidates)


class electiontests(unittest.TestCase):
    def testexample1_phragmén(self):
        votelist = [
            ("A", 10.0, ["X", "Y"]),
            ("B", 20.0, ["X", "Z"]),
            ("C", 30.0, ["Y", "Z"])]
        nomlist, electedcandidates = seq_phragmén(votelist, 2)
        self.assertEqual(electedcandidates[0].valiid, "Z")
        self.assertAlmostEqual(electedcandidates[0].score, 0.02)
        self.assertEqual(electedcandidates[1].valiid, "Y")
        self.assertAlmostEqual(electedcandidates[1].score, 0.04)

    def test_example1_approval(self):
        votelist = [
            ("A", 10.0, ["X", "Y"]),
            ("B", 20.0, ["X", "Z"]),
            ("C", 30.0, ["Y", "Z"])]
        nomlist, electedcandidates = approval_voting(votelist, 2)
        self.assertEqual(electedcandidates[0].valiid, "Z")
        self.assertAlmostEqual(electedcandidates[0].approvalstake, 50.0)
        self.assertEqual(electedcandidates[1].valiid, "Y")
        self.assertAlmostEqual(electedcandidates[1].approvalstake, 40.0)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[2] == "test":
        unittest.main()
    else:
        example1()

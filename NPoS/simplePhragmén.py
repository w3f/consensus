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
        # id of the current nominator
        self.nomid = votetuple[0]
        # staked value of the nominator
        self.budget = votetuple[1]
        # edges to candidates being voted
        self.edges = [edge(self.nomid, valiid) for valiid in votetuple[2]]
        self.load = 0


class candidate:
    def __init__(self, valiid, valindex):
        self.valiid = valiid
        self.valindex = valindex
        self.approval_stake = 0
        self.elected = False
        self.backed_stake = 0
        self.score = 0


def setup_lists(vote_list):
    '''
    Instead of Python's dict here, you can use anything with O(log n)
    addition and lookup.We can also use a hashmap like dict, by generating
    a random constant r and useing H(canid+r)
    since the naive thing is obviously attackable.
    '''
    nomlist = [nominator(vote_tuple) for vote_tuple in vote_list]
    candidate_dict = dict()
    candidate_array = list()
    num_candidates = 0

    # Get an array of candidates. ]#We could reference these by index
    # rather than pointer

    for nom in nomlist:
        for edge in nom.edges:
            valiid = edge.valiid
            if valiid in candidate_dict:
                edge.candidate = candidate_array[candidate_dict[valiid]]
            else:
                candidate_dict[valiid] = num_candidates
                newcandidate = candidate(valiid, num_candidates)
                candidate_array.append(newcandidate)
                edge.candidate = newcandidate
                num_candidates += 1
    return nomlist, candidate_array


def seq_phragmén(vote_list, num_to_elect):
    nomlist, candidates = setup_lists(vote_list)
    # Compute the total possible stake for each candidate
    # e.g. sum of the stake of all the nominators voting to each candidate.
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approval_stake += nom.budget

    elected_candidates = list()
    for round in range(num_to_elect):
        # note that the candidates[i] list and the nominator.edge.candidate[i] are mutably linked,
        # changing one will affect the other one.
        # in the following two loops this applies to edge.candidate.score and candidate.score
        for candidate in candidates:
            if not candidate.elected:
                candidate.score = 1/candidate.approval_stake
        for nom in nomlist:
            for edge in nom.edges:
                if not edge.candidate.elected:
                    edge.candidate.score += nom.budget * nom.load / edge.candidate.approval_stake

        best_candidate_index = 0
        best_score = math.inf

        # choose the best based on the computed 'approval_stake'
        for candidate in candidates:
            if not candidate.elected and candidate.score < best_score:
                best_score = candidate.score
                best_candidate_index = candidate.valindex

        elected_candidate = candidates[best_candidate_index]
        elected_candidate.elected = True
        elected_candidate.elected_pos = round
        elected_candidates.append(elected_candidate)

        # change the load of all nominators who voted for the winner
        for nom in nomlist:
            for edge in nom.edges:
                if edge.candidate.valindex == best_candidate_index:
                    edge.load = elected_candidate.score - nom.load
                    nom.load = elected_candidate.score

    # reset the backed_stake of the winners
    for candidate in elected_candidates:
        candidate.backed_stake = 0

    # set the new real backed stake value of the winners
    for nom in nomlist:
        for edge in nom.edges:
            edge.backing_stake = nom.budget * edge.load / nom.load
            edge.candidate.backed_stake += edge.backing_stake
    return nomlist, elected_candidates


def approval_voting(votelist, numtoelect):
    nomlist, candidates = setup_lists(votelist)

    # Compute the total possible stake for each candidate
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approval_stake += nom.budget
            edge.backing_stake = nom.budget/min(len(nom.edges), numtoelect)
            edge.candidate.backed_stake += edge.backing_stake

    candidates.sort(key=lambda x: x.approval_stake, reverse=True)

    electedcandidates = candidates[0:numtoelect]
    return nomlist, electedcandidates


def print_result(nomlist, electedcandidates):
    for candidate in electedcandidates:
        print(candidate.valiid, " is elected with stake ", candidate.backed_stake, "and score ", candidate.score)
    
    print()
    for nom in nomlist:
        print(nom.nomid, " has load ", nom.load, "and supported ")
        for edge in nom.edges:
            print(edge.valiid, " with stake ", edge.backing_stake, end=" ")
        print()


def equalise(nom, tolerance):
    # Attempts to redistribute the nominators budget between elected validators
    # Assumes that all elected validators have backed_stake set correctly
    # returns the max difference in stakes between sup
    
    electededges = [edge for edge in nom.edges if edge.candidate.elected]
    if len(electededges) == 0:
        return 0.0
    stakeused = sum([edge.backing_stake for edge in electededges])
    backedstakes = [edge.candidate.backed_stake for edge in electededges]
    backingbackedstakes = [edge.candidate.backed_stake for edge in electededges if edge.backing_stake > 0.0]
    if len(backingbackedstakes) > 0:
        difference = max(backingbackedstakes)-min(backedstakes)
        difference += nom.budget-stakeused
        if difference < tolerance:
            return difference
    else:
        difference = nom.budget

    # remove all backing
    for edge in nom.edges:
        edge.candidate.backed_stake -= edge.backing_stake
        edge.backing_stake = 0

    electededges.sort(key=lambda x: x.candidate.backed_stake)
    cumulativebackedstake = 0
    lastcandidateindex = len(electededges)-1

    for i in range(len(electededges)):
        backedstake = electededges[i].candidate.backed_stake
        if backedstake * i - cumulativebackedstake > nom.budget:
            lastcandidateindex = i-1
            break
        cumulativebackedstake += backedstake

    laststake = electededges[lastcandidateindex].candidate.backed_stake
    waystosplit = lastcandidateindex+1
    excess = nom.budget + cumulativebackedstake - laststake*waystosplit
    for edge in electededges[0:waystosplit]:
        edge.backing_stake = excess / waystosplit + laststake - edge.candidate.backed_stake
        edge.candidate.backed_stake += edge.backing_stake
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
        self.assertAlmostEqual(electedcandidates[0].approval_stake, 50.0)
        self.assertEqual(electedcandidates[1].valiid, "Y")
        self.assertAlmostEqual(electedcandidates[1].approval_stake, 40.0)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[2] == "test":
        unittest.main()
    else:
        example1()

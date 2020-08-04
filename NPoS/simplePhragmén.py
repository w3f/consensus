import unittest
import sys


def print_list(ll):
    for item in ll:
        print(item)


class edge:
    def __init__(self, nominator_id, validator_id):
        self.nominator_id = nominator_id
        self.validator_id = validator_id
        self.load = 0
        self.weight = 0
        self.candidate = None

    def __str__(self):
        return "Edge({}, weight = {})".format(
            self.validator_id,
            self.weight,
        )


class nominator:
    def __init__(self, nominator_id, budget, targets):
        self.nominator_id = nominator_id
        self.budget = budget
        self.edges = [edge(self.nominator_id, validator_id) for validator_id in targets]
        self.load = 0

    def __str__(self):
        return "Nominator({}, budget = {}, load = {}, edges = {})".format(
            self.nominator_id,
            self.budget,
            self.load,
            [str(e) for e in self.edges]
        )


class candidate:
    def __init__(self, validator_id, index):
        self.validator_id = validator_id
        self.valindex = index
        self.approval_stake = 0
        self.backed_stake = 0
        self.elected = False
        self.score = 0
        self.scoredenom = 0

    def __str__(self):
        return "Candidate({}, approval = {}, backed = {}, score = {}, scoredenom = {})".format(
            self.validator_id,
            self.approval_stake,
            self.backed_stake,
            self.score,
            self.scoredenom,
        )


def seq_phragmen(votelist, num_to_elect):
    nomlist, candidates = setuplists(votelist)
    calculate_approval(nomlist)

    elected_candidates = list()
    for round in range(num_to_elect):
        for candidate in candidates:
            if not candidate.elected:
                candidate.score = 1/candidate.approval_stake
        for nom in nomlist:
            for edge in nom.edges:
                if not edge.candidate.elected:
                    edge.candidate.score += nom.budget * nom.load / edge.candidate.approval_stake
        best_candidate = 0
        best_score = 1000  # should be infinite but I'm lazy
        for candidate in candidates:
            if not candidate.elected and candidate.score < best_score:
                best_score = candidate.score
                best_candidate = candidate.valindex
        elected_candidate = candidates[best_candidate]
        elected_candidate.elected = True
        elected_candidate.electedpos = round
        elected_candidates.append(elected_candidate)
        for nom in nomlist:
            for edge in nom.edges:
                if edge.candidate.valindex == best_candidate:
                    edge.load = elected_candidate.score - nom.load
                    nom.load = elected_candidate.score

    for candidate in elected_candidates:
        candidate.backed_stake = 0

    for nom in nomlist:
        for edge in nom.edges:
            if nom.load > 0.0:
                edge.weight = nom.budget * edge.load/nom.load
                edge.candidate.backed_stake += edge.weight
            else:
                edge.weight = 0
    return (nomlist, elected_candidates)


def equalise(nom, tolerance):
    # Attempts to redistribute the nominators budget between elected validators. Assumes that all
    # elected validators have backed_stake set correctly. Returns the max difference in stakes
    # between sup.

    elected_edges = [edge for edge in nom.edges if edge.candidate.elected]

    if len(elected_edges) < 2:
        return 0.0

    stake_used = sum([edge.weight for edge in elected_edges])
    backed_stakes = [edge.candidate.backed_stake for edge in elected_edges]
    backingbacked_stakes = [
        edge.candidate.backed_stake for edge in elected_edges if edge.weight > 0.0
    ]

    if len(backingbacked_stakes) > 0:
        difference = max(backingbacked_stakes)-min(backed_stakes)
        difference += nom.budget - stake_used
        if difference < tolerance:
            return difference
    else:
        difference = nom.budget

    # remove all backing
    for edge in nom.edges:
        edge.candidate.backed_stake -= edge.weight
        edge.weight = 0

    elected_edges.sort(key=lambda x: x.candidate.backed_stake)
    cumulative_backed_stake = 0
    last_index = len(elected_edges) - 1

    for i in range(len(elected_edges)):
        backed_stake = elected_edges[i].candidate.backed_stake
        if backed_stake * i - cumulative_backed_stake > nom.budget:
            last_index = i-1
            break
        cumulative_backed_stake += backed_stake

    last_stake = elected_edges[last_index].candidate.backed_stake
    ways_to_split = last_index+1
    excess = nom.budget + cumulative_backed_stake - last_stake*ways_to_split

    for edge in elected_edges[0:ways_to_split]:
        edge.weight = excess / ways_to_split + last_stake - edge.candidate.backed_stake
        edge.candidate.backed_stake += edge.weight

    return difference


def equalise_all(nomlist, maxiterations, tolerance):
    for i in range(maxiterations):
        # for j in range(len(nomlist)):
        #     nom = random.choice(nomlist)
        #     equalise(nom, tolerance)
        maxdifference = 0
        for nom in nomlist:
            difference = equalise(nom, tolerance)
            maxdifference = max(difference, maxdifference)
        if maxdifference < tolerance:
            return


def seq_phragmen_with_equalise(votelist, num_to_elect):
    nomlist, elected_candidates = seq_phragmen(votelist, num_to_elect)
    equalise_all(nomlist, 2, 0)
    return nomlist, elected_candidates


def calculateMaxScoreNoCutoff(nomlist, candidates):
    # First we compute the denominator of the score
    for candidate in candidates:
        if not candidate.elected:
            candidate.scoredenom = 1.0

    for nom in nomlist:
        denominator_contrib = 0

        for edge in nom.edges:
            if edge.candidate.elected:
                denominator_contrib += edge.weight/edge.candidate.backed_stake

        for edge in nom.edges:
            if not edge.candidate.elected:
                edge.candidate.scoredenom += denominator_contrib

    # Then we divide. Not that score here is comparable to the recipricol of the score in
    # seq-phragmen. In particular there low scores are good whereas here high scores are good.
    best_candidate = 0
    best_score = 0.0
    for candidate in candidates:
        if candidate.approval_stake > 0.0:
            candidate.score = candidate.approval_stake / candidate.scoredenom
            print("score of {} in this round is {}".format(candidate.validator_id, candidate.score))
            if not candidate.elected and candidate.score > best_score:
                best_score = candidate.score
                best_candidate = candidate
        else:
            candidate.score = 0.0

    return (best_candidate, best_score)


def electWithScore(nomlist, elected_candidate, cutoff):
    for nom in nomlist:
        for new_edge in nom.edges:
            if new_edge.validator_id == elected_candidate.validator_id:
                used_budget = sum([edge.weight for edge in nom.edges])
                new_edge.weight = nom.budget - used_budget
                elected_candidate.backed_stake += nom.budget - used_budget
                for edge in nom.edges:
                    if edge.validator_id != elected_candidate.validator_id and edge.weight > 0.0:
                        if edge.candidate.backed_stake > cutoff:
                            stake_to_take = edge.weight * cutoff / edge.candidate.backed_stake
                            new_edge.weight += stake_to_take
                            edge.weight -= stake_to_take
                            edge.candidate.backed_stake -= stake_to_take
                            elected_candidate.backed_stake += stake_to_take


def balanced_heuristic(votelist, num_to_elect, tolerance=0.1):
    nomlist, candidates = setuplists(votelist)
    calculate_approval(nomlist)

    elected_candidates = list()
    for round in range(num_to_elect):
        (elected_candidate, score) = calculateMaxScoreNoCutoff(nomlist, candidates)
        electWithScore(nomlist, elected_candidate, score)
        print("####\nRound {} max candidate {} with score {}".format(round, elected_candidate.validator_id, score))
        print_list(nomlist)

        elected_candidate.elected = True
        elected_candidates.append(elected_candidate)
        elected_candidate.electedpos = round

        equalise_all(nomlist, 10, tolerance)
        print("After balancing")
        print_list(nomlist)

    return nomlist, elected_candidates


def approval_voting(votelist, num_to_elect):
    nomlist, candidates = setuplists(votelist)
    # Compute the total possible stake for each candidate
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approval_stake += nom.budget
            edge.weight = nom.budget/min(len(nom.edges), num_to_elect)
            edge.candidate.backed_stake += edge.weight
    candidates.sort(key=lambda x: x.approval_stake, reverse=True)
    elected_candidates = candidates[0:num_to_elect]
    return nomlist, elected_candidates


def calculate_approval(nomlist):
    for nom in nomlist:
        for edge in nom.edges:
            edge.candidate.approval_stake += nom.budget


def setuplists(votelist):
    '''
    Basically populates edge.candidate, and returns nomlist and candidate array. The former is a
    flat list of nominators and the latter is a flat list of validator candidates.

    Instead of Python's dict here, you can use anything with O(log n) addition and lookup. We can
    also use a hashmap like dict, by generating a random constant r and useing H(canid+r) since the
    naive thing is obviously attackable.
    '''
    nomlist = [nominator(votetuple[0], votetuple[1], votetuple[2]) for votetuple in votelist]
    # Basically used as a cache.
    candidate_dict = dict()
    candidate_array = list()
    num_candidates = 0
    # Get an array of candidates.# We could reference these by index rather than pointer
    for nom in nomlist:
        for edge in nom.edges:
            validator_id = edge.validator_id
            if validator_id in candidate_dict:
                index = candidate_dict[validator_id]
                edge.candidate = candidate_array[index]
            else:
                candidate_dict[validator_id] = num_candidates
                newcandidate = candidate(validator_id, num_candidates)
                candidate_array.append(newcandidate)

                edge.candidate = newcandidate
                num_candidates += 1
    return nomlist, candidate_array


def run_and_print_all(votelist, to_elect):
    print("######\nVotes ", votelist)

    print("\nSequential Phragmén gives")
    nomlist, elected_candidates = seq_phragmen(votelist, to_elect)
    printresult(nomlist, elected_candidates)

    print("\nApproval voting gives")
    nomlist, elected_candidates = approval_voting(votelist, to_elect)
    printresult(nomlist, elected_candidates)

    print("\nSequential Phragmén with post processing gives")
    nomlist, elected_candidates = seq_phragmen_with_equalise(votelist, to_elect)
    printresult(nomlist, elected_candidates)

    print("\nBalanced Heuristic (3.15 factor) gives")
    nomlist, elected_candidates = balanced_heuristic(votelist, to_elect)
    printresult(nomlist, elected_candidates)


def printresult(nomlist, elected_candidates, verbose=True):
    for candidate in elected_candidates:
        print(candidate.validator_id, " is elected with stake ",
              candidate.backed_stake, "and score ", candidate.score)
    if verbose:
        for nom in nomlist:
            print(nom.nominator_id, " has load ", nom.load, "and supported ")
            for edge in nom.edges:
                print(edge.validator_id, " with stake ", edge.weight, end=", ")
            print()
        print()


def example1():
    votelist = [
        ("A", 10.0, ["X", "Y"]),
        ("B", 20.0, ["X", "Z"]),
        ("C", 30.0, ["Y", "Z"]),
    ]
    run_and_print_all(votelist, 2)


def example2():
    votelist = [
        ("10", 1000, ["10"]),
        ("20", 1000, ["20"]),
        ("30", 1000, ["30"]),
        ("40", 1000, ["40"]),
        ('2', 500, ['10', '20', '30']),
        ('4', 500, ['10', '20', '40'])
    ]
    run_and_print_all(votelist, 2)


class MaxScoreTest(unittest.TestCase):
    def test_max_score_1(self):
        votelist = [
            (10, 10.0, [1, 2]),
            (20, 20.0, [1, 3]),
            (30, 30.0, [2, 3]),
        ]
        nomlist, candidates = setuplists(votelist)
        calculate_approval(nomlist)

        best, score = calculateMaxScoreNoCutoff(nomlist, candidates)
        self.assertEqual(best.validator_id, 3)
        self.assertEqual(score, 50)

    def test_balance_heuristic_example_1(self):
        votelist = [
            (10, 10.0, [1, 2]),
            (20, 20.0, [1, 3]),
            (30, 30.0, [2, 3]),
        ]
        nomlist, winners = balanced_heuristic(votelist, 2, 0)
        self.assertEqual(winners[0].validator_id, 3)
        self.assertEqual(winners[1].validator_id, 2)

        self.assertEqual(winners[0].backed_stake, 30)
        self.assertEqual(winners[1].backed_stake, 30)

    def test_balance_heuristic_example_linear(self):
        votelist = [
            (2, 2000, [11]),
            (4, 1000, [11, 21]),
            (6, 1000, [21, 31]),
            (8, 1000, [31, 41]),
            (110, 1000, [41, 51]),
            (120, 1000, [51, 61]),
            (130, 1000, [61, 71]),
        ]

        nomlist, winners = balanced_heuristic(votelist, 4, 0)
        self.assertEqual(winners[0].validator_id, 11)
        self.assertEqual(winners[0].backed_stake, 3000)

        self.assertEqual(winners[1].validator_id, 31)
        self.assertEqual(winners[1].backed_stake, 2000)

        self.assertEqual(winners[2].validator_id, 51)
        self.assertEqual(winners[2].backed_stake, 1500)

        self.assertEqual(winners[3].validator_id, 61)
        self.assertEqual(winners[3].backed_stake, 1500)



class ElectionTest(unittest.TestCase):
    def test_phragmen(self):
        votelist = [
            ("A", 10.0, ["X", "Y"]),
            ("B", 20.0, ["X", "Z"]),
            ("C", 30.0, ["Y", "Z"]),
        ]
        nomlist, elected_candidates = seq_phragmen(votelist, 2)
        self.assertEqual(elected_candidates[0].validator_id, "Z")
        self.assertAlmostEqual(elected_candidates[0].score, 0.02)
        self.assertEqual(elected_candidates[1].validator_id, "Y")
        self.assertAlmostEqual(elected_candidates[1].score, 0.04)

    def test_approval(self):
        votelist = [
            ("A", 10.0, ["X", "Y"]),
            ("B", 20.0, ["X", "Z"]),
            ("C", 30.0, ["Y", "Z"]),
        ]
        nomlist, elected_candidates = approval_voting(votelist, 2)
        self.assertEqual(elected_candidates[0].validator_id, "Z")
        self.assertAlmostEqual(elected_candidates[0].approval_stake, 50.0)
        self.assertEqual(elected_candidates[1].validator_id, "Y")
        self.assertAlmostEqual(elected_candidates[1].approval_stake, 40.0)


def main():
    # example1()
    example2()
    # example3()


if len(sys.argv) >= 2:
    if sys.argv[1] == "run":
        main()
    else:
        unittest.main()
else:
    unittest.main()

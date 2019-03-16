# Polkadot Finality Gadget (AFG) v9000

We have a chain selection rule and block production mechanism that probably gives us consensus on a prefix of the chain including all but the most recent blocks. However we need to prove to 3rd parties that far enough back blocks are final by producing a certificate signed by _2/3_ of validators.

The idea is to run a BFT agreement algorithm similar to Tendermint or Algorand agreement but on chains rather than individual blocks so we do not need to reach agreement on each block. The algorithm will have a primary but their role will be to coordinate locking rather than propose blocks. Instead everyone will vote on their best block.

We can consider a prevote or precommit for a block as a vote for every block on that chain not already finalised. Thus we may have _2/3_ votes on many blocks in one vote but it is easy to see that all blocks with _2/3_ votes are in one chain.

We will want to change the set of participants who actively agree sometimes. To model this, we have a large set of participants who follow messages. For each voting step, there is a set of _n_ voters. We will frequently need to assume that for each such step, at most  _f < n/3_ voters are faulty. We need _n-f_ of voters to agree on finality. Whether or not block producers ever vote, they will need to be participants who track the state of the protocol.

Participants remember which block they see as currently being the latest finalised block and a chain they are locked to. This locked chain represents an estimate of which block could have been finalised already.

**Rounds**: each participant has their own idea of what the current round number is. Every prevote and precommit has an associated round number. Honest voters only vote once (for each type of vote) in each round and don't vote in earlier rounds after later ones.

Each round has two phases, each of which has an associated vote, prevote and precommit.

### Preliminaries

For block _B_, we write _\mathrm{chain}(B)_ for the chain whose head is _B_. The block number, _n(B)_ of a block _B_ is the length of _\mathrm{chain}(B)_.

For blocks _B'_, _B_, _B_ is later than _B'_ if it has a higher block number.
We write _B > B'_ or that _B_ is descendent of _B'_ for _B_, _B'_ appearing in the same blockchain with _B'_ later i.e. _B \in \mathrm{chain}(B')_ with _n(B') > n(B)_ and _B < B'_ or _B_ is an ancestor of _B'_ for _B' \in \mathrm{chain}(B)_ with _n(B) > n(B')_ . _B \geq B'_ an _B \leq B'_ are similar except allowing _B = B_. We write _B \sim B'_ or _B_ and _B'_ are on the same chain if _B<B'_,_B=B'_ or _B> B'_ and _B \nsim B'_ or _B_ and _B'_ are not on the same chain if there is no such chain.

Blocks are ordered as a tree with the genesis block as root. So any two blocks have a common ancestor but two blocks not on the same chain do not have a common descendent.

A vote _v_ for a block _B_ by a validator _V_ is a message signed by _V_ containing the blockhash of _B_ and meta information like the round numbers and the type of vote. 

We call a set _S_ of votes tolerant if the number of validators with more than one vote in _S_ is at most _f_. We say that _S_ has supermajority for a block _B_ if the set of validators with votes for blocks _\geq B_ has size at least _(n+f+1)/2_.

The _2/3_-GHOST function _g(S)_ takes a set _S_ of votes and returns the block _B_ with highest block number such that _S_ has a supermajority for _B_. If there is no such block, then it returns `nil`. (if _f \neq \lfloor (n-1)/3 \rfloor_, then this is a misnomer and we may change the name accordingly.)

Note that, if _S_ is tolerant, then we can compute _g(S)_ by starting at the genesis block and iteratively looking for a child of our current block with a supermajority, which must be unique if it exists. Thus we have:
**Lemma 1**: Let _T_ be a tolerant set of votes. Then

1. The above definition uniquely defines _g(T)_
2. If _S \subseteq T_ has _g(S) \neq_ nil, then _g(S) \leq g(T)_.
3. If _S_i \subseteq T_ for _1 \leq i \leq n_ then all non-nil _g(S_i)_ are on a single chain with head _g(T)_.

Note that we can easily update _g(S)_ to _g(S \cup \{v\})_, by checking if any child of _g(S)_ now has a supermajority.

3 tells us that even if validators see different subsets of the votes cast in a given voting round, this rule may give them different blocks but all such blocks are in the same chain under this assumption. 

We say that it is possible for a set _S_ to have a supermajority for _B_ if _2f+1_ validators either vote for a block _\not \geq B_ or equivocate in _S_. Note that if _S_ is tolerant, it is possible for _S_ to have a supermajority for _B_ if and only if there is a tolerant _T \supseteq S_ that has a supermajority for _B_.


We say that it is impossible for any child of _B_ to have a supermajority in _S_ if _S_ has votes from at least _2f+1_ validators and it is impossible for _S_ to have a supermajority for each child of _B_ appearing on the chain of any vote in _S_. Again, provided _S_ is tolerant, this holds if and only if for any possible child of _B_, there is no tolerant _T \subset S_ that has a supermajority for that child.

Note that it is possible for an intolerant _S_ to both have a supermajority for _S_ and for it to be impossible to have such a supermajority under these definitions, as we regard such sets as impossible anyway.

**Lemma 2**
(i) If _B' \geq B_ and it is imposible for _S_ to have a supermajority for _B_, then it is imposible for _S_ to have a supermajority for _B'_.
(ii) If _S \subseteq T_ and it is impossible for _S_ to have a supermajority for _B_
(iii) If _g(S)_ exists and _B \nsim g(S)_ then it is impossible for _S_ to have a supermajority for _B_.

## Algorithm

We let _V_{r,v}_ and _C_{r,v}_ be the sets of prevotes and precommits respectively recieved by _v_ from round _r_ at the current time.

We define _E_{r,v}_, _v_'s estimate of what might have been finalised in round _r_, to be the last block in the chain with head _g(V_{r,v})_ that it is possible for _C_{r,r}_ to have a supermajority for. If either _E_{r,v} < g(V_{r,v})_ or it is impossible for _C_{r,v}_ to have a supermajority for any children of _g(V_{r,v})_,, then we say that (_v_ sees that) round _r_ is completable. _E_{0,v}_ is the genesis block (if we start at _r=1_).

We have a time bound _T_, that we hope is enough to send messages and gossip them to everyone. 

In round _r_ an honest validator _v_ does the following:

1. _v_ can start round _r > 1_ when round _r-1_ is completable and _v_ has cast votes in all previous rounds where they are a voter. Let _t_{r,v}_ be the time we start round _r_.

2. At time _t_{r,v}_, if _v_ ais the primary of this round and has not finalised _E_{r-1,v}_ then they broadcast _E_{r-1,v}_. If thy have finalised it, they can broadcast _E_{r-1,v}_ anyway (but don't need to).

3. If _v_ is a voter for the prevote of round _r_, _v_ waits until either it is at least time _t_{r,v}+2T_ or round _r_ is completable, then broadcasts a prevote. They prevote for the head of the best chain containing _E_{r-1,v}_ unless we recieved a block _B_ from the primdary and _g(V_{r-1,v}) \geq B > E_{r-1,v}_, in which case they use the best chain containing _B_ instead.

4. If _v_ is a voter for the precommit step in round _r_, then they wait until _g(V_{r,v}) \geq E_{r-1,v}_ and one of the following  conditions holds
(i) it is at least time _t_{r,v}+4T_, 
(ii) round _r_ is completable or
(iii) it is impossible for _V_{r,v}_ to have a supermajority for any child of _g(V_{r,v})_,
and then broadcasts a precommit for _g(V_{r,v})_ _( (iii) is optional, we can get away with just (i) and (ii))_.


### Finalisation

If, for some round _r_, at any point after the precommit step of round _r_, we have that _B=g(C_{r,v})_ is later than our last finalised block and _V_{r,v}_ has a supermajority, then we finalise _B_. We may also send a commit message for _B_ that consists of _B_ and a set of precommits for blocks _\geq B_ (ideally for _B_ itself if possible see "Alternatives to the last blockhash" below). 

To avoid spam, we only send commit messages for _B_ if we have not receive any valid commit messages for _B_ and its decendents and we wait some time chosen uniformly at random from _[0,1]_ seconds or so before broacasting.

If we recieve a valid commit message for _B_ for round _r_, then it contains enough precommits to finalise _B_ itself if we haven't already done so, so we'll finalise _B_ as long as we are past the precommit step of round _r_.

# Analysis

## Accountable Safety

The first thing we want to show is asynchronous safety if we have at most _f_ Byzantine validators:

**Theorem 1**: If the protocol finalises any two blocks _B,B'_ that have valid commit messages sent are on the same chain, then there are at least _f+1_ Byzantine voters who all voted in a particular vote. Furthermore, there is a synchronous procedure to find such a set.

The challenge procedure works as follows: If _B_ and _B'_ are committed in the same round, then the union of their precommits must contain at least _f_ equivocations, so we are done. Otherwise _B_ was commited in round _r_ and _B'_ in round _r' > r_ say. Then we ask the at least _n-f_ validators who precomitted _\geq B'_ in round _r_ in the commit message, why they precommited.

We ask queries of the following form: 

- Why was _E_{r''-1} \not\geq B_  when you prevoted for or precomitted to _B'' \not\geq B_ in round _r'' > r_?

Which any honest validator should be able to respond to as is shown in Lemma **3** below. 

The response is of the following form:

- A either a set _S_ of prevotes for round _r''-1_ or a set _S_ of precommits for round _r''-1_  or  such that it is impossible for _S_ to have a supermajority for _B_.

If no validator responds, then we  have _n-f_ Byzantine validators. If any do, then if _r'' > r+1_,  we can ask the same query for _n-f_ validators in round _r''-1_.

If any responded and _r''=r+1_, then we have either a set _S_ of prevotes or precommits in round _r_ that it is impossible for _S_ to have a supermajority for _B_ in round _r_.

If _S_ is a set of precommits, then if we take the union of _S_ and the set of precommits in the commit message for _B_, then the resulting set of precommits for round _r_ has a supermajority for _B_ and it is impossible for it to have a supermajority for _B_. This is possible if the set is not tolerant and so there must be at least _f+1_ voters who equivocate an so are Byzantine.

If we get a set _S_ of prevotes for round _r_ that does not have a supermajority for _B_, then we need to ask a query of the form

- Which prevotes for round _r_ have you seen?

to all the voters of precommit in the commit message for _B_  who voted for blocks _B'' \geq B_. There must be _n-f_ such validators and a valid respone to this query is a set _T_ of prevotes for round _r_ with a supermajority for _B''_ and so a supermajority for _B_.

If any give a valid response, by a similar argument to the above, _S \union T_ will have _f+1_ equivocations.

So we either discover _f+1_ equivocations in a vote or else _n-f > f+1_ voters fail to validly respond like a honest voter could do to a query.

**Lemma 3** An honest validator can answer the first type of query.

We first need to show that for any prevote or precommit in round _r_ cast by an honest validator _v_ for a block _B''_, at the time of the vote we had _B'' \geq E_{r-1,v}_. Prevotes should be for the head of a chain containing either _E_{r-1,v}_ or _g(V_{r,v})_ Since _g(V_{r,v}) \geq E_{r-1},v_, in either case we have _B'' \geq E_{r-1,v}_. Precommits should be for _g(V_{r,v})_ but _v_ waits until _g(V_{r,v}) \geq E_{r-1,v}_ befor precommiting so again this holds.

Thus if _B'' \not\geq B_, then we had _E_{r-1,v} \not\geq B_.
Next we need to show that if we had _E_{r-1,v} \not\geq B_ at the time of the vote then we can respond to the query validly. If _B_ wasn't on the same chain with _g(V_{r-1,v})_, then by Lemma 2 (iii), it was impossible for _V_{r-1,v}_ to have a supermajority for _B_. If it was on the same chain as _g(V_{r,-1v})_, then it was on the same chain as _E_{r-1,v}_ as well. Since _E_{r-1,v} \not\geq B_, in this case we must have _B > E_{r-1,v}_. However, possibly using that round _r-1_ is completable, it was impossible for _C_{r-1,v}_ to have a supermajority for any child of _E_{r-1,v}_ on the same chain with _g(V_{v,r})_ and in particular for the child of _E_{r-1,v}_ on _\textrm{chain}(B)_. By Lemma 2 (i), this means _C_{r-1,v}_ did not have a supermajority for _B_.

Thus we have that, at the time of th vote, for one of _V_{r-1,v}_, _C_{r-1,v}_, it was imposible to have a supermajority for _B_. The current sets _V_{r-1,v}_ and _C_{r-1,v}_ are supersets of those at the time of the vote, and so by Lemma 2 (ii), it is still impossible. Thus _v_ can respond validly.


This is enough to show Theorem 1. Not that if _v_ sees a commit message for a block _B_ in round _r_ and has that _E_{r',v} \not\geq B_, for some completable round _r' \geq r_, then they should also be able to start a challenge procedure that succesfully identifies at least _f+1_ Byzantine voters in some round. Thus we have that:

**Lemma 4**
If there at most _f_ Byzantine voters in any vote, _B_ was finalised in round _r_ and an honest participant _v_ sees that round _r' \geq r_ is completable, then _E_{r',v} \geq B_.

## Liveness

We show the protocol is deadlock free and also that it finalises new blocks quickly in a weakly synchronous model.

Let's define _V_{r,v,t}_ be the set _V_{r,v}_ at time _t_ and similarly for _C_{r,v,t}_ and the block _E_{r,v,t}_ .


**Lemma 5** Let _v,v'_ be (possibly identical) honest particpants, _t,t'_ be times and _r_ be a round. Then if _V_{r,v,t} \subseteq V_{r,v',r'}_ and _C_{r,v,t} \subseteq C_{r,v',r'}_, all these sets are tolerant and _v_ sees that _r_ is completable at time _t_, then _E_{r,v,t} \leq E_{r,v',t'}_ and _v'_ sees that _r_ is completable at time _t'_.

**Proof:** Since _v_ sees that _r_ is completable at time _t_, _V_{r,v,t}_, _C_{r,v,t}_ each contain votes from _n-f_ voters and so the same holds for _V_{r,v',t'}_ and _C_{r,v',t'}_. 
By Lemma 1, _g(V_{r,v',t'}) \geq g(V_{r,v,t})_. Using Lemma 2, since it is impossible for _C_{r,v,t}_ to have a supermajority for any children of _g(V_{r,v,t}_, it is impossible for _C_{r,v',t'})_ as well and so _E_{r,v',t'} \leq g(V_{r,v,t})_. But now _E_{r,v,t}_,_E_{r,v',t'}_ are the last blocks on _\textrm{chain}(g(V_{r,v,t}))_ that it is possible for _C_{r,v,t},C_{r,v',t'}_ respectively to have a supermajority for. Thus by Lemma 2 (ii), _E_{r,v',t'} \leq E_{r,v,t}_.

### Deadlock Freeness

Now we can show deadlock freeness for the asynchronous gossip network model, when a message that is sent or recieved by any honest participant is eventually recieved by all honest participants.

**Proposition 6** Suppose that we are in the aynchonous gossip network model and that at most _f_ voters for any vote are Byzantine. Then the protocol is deadlock free.

**Proof:** We need to show that if all honest participants reach some vote, then all of them eventually reach the next.

If all honest voters reach a vote, then they will vote and all honest participants see their votes. We need to deal with the two conditions that might block the algorithm even then. To reach the prevote of round _r_, a particpant may be held up at the condition that round _r-1_ must be completable. To reach the precommit, a voter may be held up by the condition that _g(V_{r,v}) \geq E_{r-1,v}_.

For the first case, the prevote, let _S_ be the set of all prevotes from round _r-1_ that any honest voter saw before they precommitted in round _r-1_. By Lemma 1, when voter _v'_ precommitted, they do it for block _g(V_{r-1,v'}) \leq g(S)_. Let _T_ be the set of precommits in round _r_ cast by honest voters. Then or any block _B \not\leq g(S)_, _T_ does not contain any votes that are _\geq B_ and so it is impossible for _T_ to have a supermajority for _B_. In particular, it is impossible for _T_ to have a supermajority for any child of _g(S)_. 

Now consider a voter _v_. By our network assumption, there is a time _t_ by which they have seen the votes in _S_ and _T_. Consider any _t' \geq t_. At this point we have _g(V_{r,v,t;}) \geq g(S)_. It is impossible for _C_{r,v,t'}_ to have a supermajority for any child of _g(S)_ and so _E_{r-1,v,t'} \leq g(S)_, whether or not this inequality is strict, we satisfy one of the two conditions for _v_ to see that round _r-1_ is completable at time _t'_. Thus if all honest voters reach the precommit vote of round _r-1_, all honest voters reach the prevote of round _r_.

Now we consider the second case, reaching the precommit. Note that any honest prevoter in round _r_ votes for a block _B_v \geq E_{r-1,v,t_v}_ where _t_v_ is the time they vote. Now consider any honest voter for the precommit _v'_. By some time _t'_, they have recieved all the messages recieved by each honest voter _v_ at time _t_v_ and _v'_'s prevote. Then by Lemma 4, _B_v \geq E_{r-1,v,t_v} \geq E_{r-1,v',t'}_. Since _V_{r,v',t'}_ contains these _B_v_, _g(V_{r,v',t'}) \geq  E_{r-1,v',t'}_. Thus if all honest voters prevote in round _r_, eventually all honest voters precommit in round _r_.

An easy induction completes the proof of the proposition.

### Weakly synchronous liveness

Now we consider the weakly synchronous gossip network model. The idea that there is some global stabilisation time(_\textrm{GST}_) such that any message recieved or sent by an honest participant at time _t_ is recieved by all honest paticipants at time _\max\{t,\textrm{GST}\}+T_.

Let _t_r_ be the first time any honest particpant enters round _r_ i.e. the minimum over honest participants _v_ of _t_{r,v}_.

**Lemma 7** Assume the weakly synchronous gossip network model and that each vote has at most _f_ Byzantine voters. Then if _t_r \geq \textrm{GST}_, we have that 
(i) _t_r \leq t_{r,v} \leq t_r+T_ for any honest particpant _v_,
(ii) no honest voter prevotes before time _t_r+2T_,
(iii) any honest voter _v_ precommits at the latest at time _t_{r,v}+4T_,
(iv) for any honest _v_, _t_{r+1,v} \leq t_r + 6T_.


**Proof:** Let _v'_ be one of th first valiators to enter round _r_ i.e. with _t_{r,v'}=t_r_. By our network assumption, all messages recieved by _v'_ beore they ended are recieved by all honest participants before time _t_r+T_. In particular at time _t_r_, _v'_ sees that all previous rounds are completable and so by Lemma 4, so does every other honest validator by time _t_r+T_. Also since for _r' < r_, at some time _s_{r'} \leq t_r_ _g(V_{r',v',s_r'}) \geq E_{r',v',s_r'}_, again by Lemma 4, for all honest _v_, _g(V_{r',v,t_r+T}) \geq E_{r',v,t_r+T}_. Looking at the conditions for voting, this means that any honest validator does not need to wait before voting in any round _r' \leq r_. Thus they cast any remaining votes and enter round _r_ by time _t_r + T_. This shows (i).

For (ii), note that the only reason why an honest voter would not wait until time _t_{r,v}+2T \geq t_r+ 2T_ is when _n-f_ voters have already prevoted. But since some of those _n-f_ votes are honest, this is impossible before _t_r+2T_

Now an honest voter _v''_ prevotes at time _t_{r,v''}+2T \leq t_r +3T_ and by our network assumptions all honest validators recieve this vote by time _t_r+4T_. An honest voter for the precommit _v_ has also recieved all messages that _v''_ recieved before they prevoted by then. Thus the block they prevoted has _B_{v''} \geq E_{r-1,v''} \geq E_{r-1,v,t_r+4T}_, since this holds for every honest voter _v''_, _g(V_{r,v,t_r+4T}) \geq E_{r-1,v,t_r+4T}_. Thus they will precommit by time _t_{r,v}+4T_ which shows (iii).

By the network assumption an honest voter _v'_'s precommit will be recieved by all honest validators _v_ by time _t_{r,v'}+ 5T \leq t_r+6T_. Since _v_ will also have recieved all prevotes _v_ say when they precommitted by this time, their vote _B_{v'}_ will have _B_{v'}=g(V_{r,v'}) \leq g(V_{r,v,t_r+6T})_. Thus _C_{r, v, t_r+6T}_ contains precommits from _n-f_ voters _v'_ with _B_{v'} \leq g(V_{r,v,t_r+6T})_ and thus it is impossible for _C_{r,v,t_r+6T}_ to have a supermajority for any children of _g(V_{r,v, t_r+6T})_. Thus _v_ sees that round _r_ is comletable at time _t_r+6T_. Since they have aleady prevoted and precommited if they were a voter, they will move to round _r+1_ by at latest _t_t+6T_. This is (iv).


**Lemma 8**
Suppose _t_r \geq GST_ and very vote has at most _f_ Byzanyine voters. Let _H_r_ be the set of prevotes ever cast by honest voters in round _r_. Then

(a) any honest voter precommits to a block _\geq  g(H_r)_,

(b) every honest paticipant finalises _g(H_r)_ by time _t_r+6T_.

**Proof:** For (a), we separate into cases based on which of the conditions (i)-(iii) that we wait for to precommit hold.

For (i), all honest voters prevote in round _r_ by time _t_r+3T_. So any honest voter _v_ who precommits at or after time _t_{r,v}+4T \geq t_r+4T_ has recieved all votes in _H_r_ and by Lemma 1, precommits to a block _\geq g(H_r)_.

For (ii), we argue that no honest voter commits a block _\not\geq g(H_r)_ first. The result will then follow by an easy induction once the other cases are dealt with. Suppose that no honest voter has precommited a block _\not \geq g(H_r)_ so far and that a voter _v_ votes early because of (ii).

Note that, since we assume that all precommits by honest voters so far were _\geq g(H_r)_, it is possible for _C_{r,v}_ to have a supermajority for _g(H_r)_. For (ii) to hold for a voter _v_ i.e for round _r_ to be completable, it must be the case that either it is impossible for _C_{r,v}_ to have a supermajority for _g(V_{r,v})_ or else be impossible for _C_{r,v}_ to have a supermajority for any children of _g(V_{r,v})_. By Lemma 2, we cannot have _g(V_{r,v}) < g(H_r)_. But by Lemma 1, these are on the same chain and so _g(V_{r,v}) \geq g(H_r)_. Since this is the block _v_ precommits to, we are oone in case (ii)

For (iii), let _v_ be the voter in question. Note that since _n-f_ honest voters prevoted _\geq g(H_r)_, it is possible for _V_{r,v}_ to have a supermajority for _g(H_r)_. By Lemma 1, _g(V_{r,v})_ is on the same chain as _g(H_r)_. For (iii), it is impossible for _V_{r,v}_ to have a supermajority for any children of _g(V_{r,v})_. If we had _g(V_{r,v}) < g(H_r)_, by Lemma 2, this would mean that it would be impossible for _V_{r,v}_ to have a supermajority for _g(H_r)_ as well. So it must be that _g(V_{r,v} )\geq g(H_r)_ as required.

For (b), combining (a) and Lemma 7 (iii), we have that any honest voter _v_ precommits _\geq g(H_r)_ by time _t_{r,v}+4T_. By our netork assumption, all honest particpants recieve these precommits by time _t_r+6T_ and so finalis _g(H_r)_ if they have not done so already.


**Lemma 9** Suppose that _t_r \geq GST_, the primary _v_ of round _r_ is honest and no vote has more than _f_ Byzantine voters. Let _B=E_{r-1,v,t_{v,r}}_ be the block _v_ broacasts if it is not final. Then every honest prevoter prevotes for the best chain including _B_ and all honest voter finalise _B_ by time _t_r+6T_.

**proof**: By Lemma 7 and our nwtork asumptions, no honet voter  prevotes befor time _t_r+2T \geq t_{r,v}+2T_ and so at this time, they will have seen all prevotes and precommits seen by _v_ at _t_{r,v}_ and the block _B_ if _v_ broacast it then. By Lemma 5, any honest voter _v'_ has _E_{r-1,v'} \leq B \leq g(V_{r-1,v}_ then.

So if the primary broadcast _B_, then _v'_ prevotes for the best chain including _B_. If the primary did not broadcast _B_, then they finalise it. By Lemma 4, it must be that _E_{r-1,v'} \geq B_ and so _E_{r-1,v'}=B_ and so in this case _v'_ also prevots for th best chain including _B_.

Since all honest voters prevote _\geq B_, _g(H_r) \geq B_ and so by Lemma 8, all honest particpants finalise _B_ by time _t_r+6T_




**Lemma 10** Suppose that _t_r \geq GST+T_ and the primary of round _r_ is honest. 
Let _B_ be the latest block that is ever finalised in rounds  _<r_ (even if no honest paticpant finalises it until after _t_r_). If all honest voters for the prevote in round _r_ agree that the best chain containing _B_ include the same child _B'_ of _B_, then they all finalises some child of _B_ before _t_r+6T_.

**proof** By Lemma 4, any honest particapant sees that _E_{r-1} \geq B_ during round _r_. Let _v_ be the pimary of round _r_ and _B''=E_{r-1,v,t_{r,v}}_. If _B'' > B_, then by Lemma 9, all honest validators finalise _B''_ by time _t_r+6T_ which means they finalised a child of _B_. If _B''=B_, then by Lemma 8, all honest voters prevote for th bst chain including _B_. By assumption these chains inclue _B'_ and so _g(H_r) \geq B_. By Lemma 8, this means that _B'_ is finalised by time _t_r+6T_.







#### Recent Validity

**Lemma 11** Suppose that _t_r \geq GST_, the primary of round _r_ is honest and all votes have at most _f_ Byzantine voters. Let _B_ be a block that no prevoter in round _r_ saw as being in the best chain of an ancstor of _B_ at the time they prevoted. Then either all honest validators finalise _B_ before time _t_r+6T_ or no honest validator ever has _g(V_{r,v}) \geq B_ or _E_{r,v} \geq B_.

**proof** Let _v'_ be the primary of round _r_ and let _B'=E_{r-1,v',t_{r,v'}}_. If _B' \geq B_, then by Lemma 9, all honest validators finalise _B_ by time _t_r+6T_. If _B' \not\geq B_, then by Lemma 9, no honest validator prevotes _\geq B_ and so no honest validator ever has _g(V_{r,v}) \geq B_.


**Corollary 2** For _t - 6T > t' \geq GST_, suppose that an honest validator finalises _B_ at time _t_ but that no honest voter has seen _B_ as in the best chain containing some ancestor of _B_ in between times _t'_ and _t_, then at least _(t-t')/6T - 1_ rounds in a row had Byzantine primaries.




## Practicalities

### Alternatives to the last block hash

The danger with voting for the last blockhash in the best chain is that maybe no one else will have seen and processed the next block. It would also be nice to make the most of BLS multisig/aggregation, which allows a single signature for many messages/signers than can be checked in time proportional to the number of different mssages signed. 

To get round the first alone, it might be better to vote for a block 3/4 along (rounding further) the unfinalised chain , rather than for the head.

But the second suggests that maybe we should be including signatures for several of the latest blocks in a chain. We could include that last 2 or 3. We could also do e.g. the the blocks with block numbers with the last 2 multiples of each power of two since the last finalised block, which gives log unfinalis chain length messages but should have many blocks in common.

When presented with a vote that includs many blocks, we should interpret them as being for the last block we've seen if any. Then we need to be able to update that vote to a later block when that is seen. This retains monotonicity of a supermajrity for/ it is impossible to have a supermajority for over time.

It does not matter if some of the votes are for a block that does not exist as everyone will ignore that part of the vote. But including votes for block that are seen but are not on a chain is an equivocation and is slashable. We need to count such votes as votes for the head of every chain in the vote (as someone might interpret them as for any one of them).

Then if we need to BLS aggregate votes that are _\geq B_ for a commit message or query response, it is ok to use any vote that is _\geq B_, not necessarily the vote for the head. This should reduce the number of blockhash signatures, in the optimistic case down to 1.

###  Block production rule

If we adopt that rule that block producers should build on the best chain including the finalised block, then if we don't finalise another block this will eventually include some prefix beyond the finalised block, and therefore the protocol is live by Lemma 11.

But the issue is that if agreement is much slower than block production, then we might have a prevote for a short chain on the last finalised block, then the best chain does not include that block and we build a long chain that is eventually never finalised. This could be fixed by building on _E_{r-1}_ or _E_r_. But if we do that, and these change very quickly, then we may never come to agreement on the best chain. 

So we have two possible chain selection rules for block producers:

1. Build on the best chain including the last finalised block B.
2. Build on best chain including whichever of _\{E_r,E_{r-1},B\}_ is latest and _\geq B_.

1 is better if finalisation is happening quickly compared to block production and 2 is best if block production is much faster. We could also consider hybrid rules like adopt 1 unless we see that the protocol is stuck or slow, then we switch to 2.

## Why?

### Why do we wait at the end of a round and sometimes before precommitting?

If the network  is badly behaved, then these steps may involve waiting an arbitrarily long time. When the network is well behaved (after the GST in our model), we should not be waiting. Indeed there is little point not waiting to recieve 2/3 of voters' votes as we cannot finalise anything without them. But if the gossip network is not perfect, an some messages never arrive, then we may need to implement voters asking other voters for votes from previous rouns in a similar way to the challenge procedure, to avoid deadlock.

In exchange for this, we get the property that we do not need to pay attention to votes from before the previous round in order to vote correctly in this one. Without waiting, we could be in a situation where we might have finalised a block in some round _r_, but the network becomes unreliable for many rounds and gets few votes on time, in which case we would need to remember the votes from round _r_ to finalise the block later. 

### Why have a primary?

We only need the primary for liveness. We need some form of coordination to defeat the repeated vote splitting attack. The idea behind that attack is that if we are in a situation where almost 2/3 of voters vote for something and the rest vote for another, then the Byzantine voters can control when we see a supermajority for something. If they can carefully time this, they may be able to split the next vote. Without the primary, they could do this for prevotes, getting a supermajority for a block _B_ late, then split precommits so we don't see that it is impossible fo thre to be a supermajority for _B_ until late. If _B_ is not the best block given the last finalised block but _B'_  with the same block number, they could stop either from being finalised like this even if the (unknown) fraction of Byzantine players is small.

When the network is well-behaved, an honest primary can defeat this attack by deciding how much we should agree on. We could also use a common coin for the same thing, where poeple would prevote for either the best chain containing _E_{r-1,v}​_ or _g(V_{r-1,v})​_ depending on the common coin. With on-chain voting, it is possible that we could use probabilistic finality of the block production mechanism - that if we don't finalise a block and always build on the best hain containing the last finalised block then not only will the best chain eventually converge, but if a block is behind the head of the best chain, then with positive probability, it will eventually be in the best chain everyone sees.

In our setup, having a primary is the simplest option for this.

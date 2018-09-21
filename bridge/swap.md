

We envision a bridge that manages security for atomic swaps by observing the bitcoin blockchain, but does not itself hold bitcoins, and only holds dots as stake.  Aside from the bridge nodes and polkadot infrastructure, we have two customers, Paula who trade dots and Brit who trades bitcoin, although atomicity could generalise either to a group.  

I'll give a handy wavy sketch that should be informed by going over ZKCP literature: 

Step 0.  Paula's offer of Dot and Brit's offer of BTC get matched via some trading network, placing them into communication.  I donno if MPC helps here.

Step 1.  Paula and Brit negotiate their transaction: 
 - Paula provides Brit with her BTC wallet hash and her bridge supported test for considering the transaction settled on bitcoin.  
 - If Brits consider the test reasonable, then Brit secretly crafts but does not publish her BTC payment x to Paula, and gives Paula the hash of x.
 
Step 2.  Paula submits a bridge parachain transaction y to Brit that registers the trade with the bridge and time locks the funds she wishes to trade.  Registration reveals the test, the Dot and BTC amounts, Paula's BTC wallet hash, and the BTC transaction hash. 

Step 3.  After the parachain transaction is finalised, Brit submits her BTC transaction x, or maybe gives it to Paula so she can submit it.  If Brit does not do so fast enough then Paula's time lock expires.  

Step 4.  The bridges threshold sign y releasing the funds, after recognising that x matches its hash commitment, sends the correct BTC amount to Paula's BTC hash, and has persisted long enough to past the test.  

We could improve perceived latency for Brit, and maybe simplify client code, by having Brit threshold encrypt x to the bridges in step 2, so the bridges carry out step 3 after finalising.  We expect polkadot to be fast though, so imho Brit should prefer the latency and simpler security model above.  Also I'd expect the above scheme simplifies bridge code far more than alternative schemes simplify client code.



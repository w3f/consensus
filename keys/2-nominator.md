


## Nominator keys

We support staked account keys being air gapped by having a layer called nominator keys that lies strictly between staked account keys and session keys.  In this post, we shall discuss the certificate schemes delegating from staked account keys to nominator keys and delegating from nominator keys to session keys, which includes several unanswered questions.

In principle, any certificate format should work for nominator keys, but some certificate schemes provide more flexibility, while others save space.  We do not require much flexibility per se, but these certificates must live inside the staked account, and have some associated data:

 - block hash and height when staked,
 - unstaking block hash and height, if unstaking, and
 - permissions, like only block production, validator nomination, and validator operator.

### One vs two layer

We can support nominated proof-of-stake with only one layer per se.  We'd have validator operator nominator keys point directly to their validator's current session keys, while nominator keys that only nominate point to validator operating nominator keys.  We expect all nominator keys act as owners for a block protection node's session key.

We could require another layer, either by envisioning the session key itself as two layer, or by adding a second layer of nominator key.  I think a split session key simplifies session key rollover, which improves forward security and thus reduces the benefits of compromising nodes.  

### Certificate location

We could either store certificates with account data, or else provide certificates in protocol interactions, but almost surely the certificate delegating from the staked account to the nominator key belongs in the account data.

We should take care with the certificates from the nominator key to the session key because the session key requires a proof-of-possesion.  If we place them into the account, then there is a temptation to trust them and not check the proof-of-possesion ourselves.  If we provide them  in interactions then there is a temptation to check the proof-of-possesion repeatedly.  We might consider storing them in some self-checked account data separate from the account data for which nodes trust the chain.  

### Certificate size

We could save some space by using implicit certificates to issue nominator keys, as implemented in [`schnorr-dalek/src/cert.rs`](https://github.com/w3f/schnorr-dalek/blob/master/src/cert.rs#L181).  In other words, an accounts nominator key could be defined by an additional 32 bytes attached to the account, along with any associated data.  

We need to hold a conversation about (a) what form this associated data should take, and (b) if the space savings are worth the complexity of an implicit certificates scheme, mostly [reviewing the literature](https://github.com/w3f/schnorr-dalek/issues/4).  

We clearly need non-implicit certificates for non-owning nominators.  As a result, we might actually reduce the code complexity by not using implicit certificates in the nomination process.  We might then achieve better code reuse by not using implicit certificates anywhere. 


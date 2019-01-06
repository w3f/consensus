# Signing keys in Polkadot

In this post, we shall first give a high level view of the various signing keys planned for use in Polkadot.  We then turn the discussion towards the certificate chain that stretches between staked account keys and the session keys used for our proof-of-stake design.  In other words, we aim to lay out the important questions on the "glue" between keys rolls here, but first this requires introducing the full spectrum of key rolls.

We have roughly four cryptographic layers in Polkadot:

 - *Account keys* are owned by users and tied to one actual dot denominated account on Polkadot.  Accounts could be staked/bonded, unstaked/unbonded, or unstaking/unbonding, but only an unstaked/unbonded account key can transfer dots from one account to another.
 - *Nominator keys* provide a certificate chain between staked/bonded account keys and the session keys used by nodes in block production or validating.  As nominator keys cannot transfer dots, they insulate account keys, which may remain air gapped, from nodes actually running on the internet.
 - *Session keys* are actually several keys kept together that provide the various signing functions required by validators, including a couple types of verifiable random function (VRF) keys.
 - *Transport layer signing keys* are used by libp2p to authenticate connections between nodes.  We shall either certify these with the session key or perhaps include them directly in the session key.


## Account keys

We believe Polkadot accounts should primarily use Schnorr signatures with both public keys and the `R` point in the signature encoded using the [Ristretto](https://ristretto.group) point compression for the Ed25519 curve.  We should collaborate with the [dalek ecosystem](https://github.com/dalek-cryptography) for which Ristretto was developed, but provide a simpler signature crate, for which [schnorr-dalek](https://github.com/w3f/schnorr-dalek) provides a first step.

I'll write a another comment outlining the reasons for this choice, while providing only a high level summary here:


Account keys must support the diverse functionality desired of account keys on other systems like Ethereum and Bitcoin.  As such, our account keys shall use Schnorr signatures because these support fast batch verification and hierarchical deterministic key derivation ala [BIP32](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#Child_key_derivation_CKD_functions). All features from the [Bitcoin Schnoor wishlist](https://github.com/sipa/bips/blob/bip-schnorr/bip-schnorr.mediawiki) provides a case for Schnorr signatures matter too, like

 - interactive threshold and multi-signaturtes, as well as
 - adaptor, and perhaps even blind, signatures for swaps and payment channels. 


We make conservative curve choices here because account keys must live for decades.  In particular, we avoid pairing-based cryptography and BLS signatures for accounts, at the cost of true aggregation of the signatures in a block when verifying blocks, and less interactive threshold and multi-signaturtes. [1]. 

In the past, there was a tricky choice between the more secure curves:

 - miss-implementation resistance is stronger with Edwards curves, including the Ed25519 curve, but
 - miss-use resistance in stronger when curves have cofactor 1, like secp256k1.

In fact, miss-use resistance was historically a major selling point for Ed25519, which itself is a Schnorr variant, but this miss-use resistance extends only so far as the rudimentary signature scheme properties it provided.  Yet, any advanced signature scheme functions, beyond batch verification, break precisely due to Ed25519's miss-use resistance.  In fact, there are tricks for doing at least hierarchical deterministic key derivation on Ed25519, as implemented in [hd-ed25519](https://github.com/w3f/hd-ed25519), but almost all previous efforts [produced insecure results](https://forum.web3.foundation/t/key-recovery-attack-on-bip32-ed25519/44).

We observe that secp256k1 provides a good curve choice from among the curves of cofactor 1, which simplify make implementing fancier protocols.  We do worry that such curves appear at least slightly weaker than Edwards curves.   We worry much more than such curves tend to be harder to implement well, due to having incomplete addition formulas, and thus require more review (see [safecurves.cr.yp.to](https://safecurves.cr.yp.to)).  We could select only solid implementations for Polkadot itself, but we cannot control the implementations selected elsewhere in our ecosystem, especially by wallet software.

In short, we want an Edwards curve but without the cofactor, which do not exist, except..

In Edwards curve of with cofactor 4, [Mike Hamburg's Decaf point compression](https://www.shiftleft.org/papers/decaf/) only permits serialising and deserialising points on the subgroup of order $l$, which provides a perfect solution.  [Ristretto](https://ristretto.group) pushes this point compression to cofactor 8, making it applicable to the Ed25519 curve.  Implementations exist in both [Rust](https://doc.dalek.rs/curve25519_dalek/ristretto/index.html) and [C](https://github.com/Ristretto/libristretto255).  If required in another language, the compression and decompression functions are reasonable to implement using an existing field implementation, and fairly easy to audit.  

In the author's words, "Rather than bit-twiddling, point mangling, or otherwise kludged-in ad-hoc fixes, Ristretto is a thin layer that provides protocol implementors with the correct abstraction: a prime-order group."


[1] Aggregation can dramatically reduce signed message size when applying numerous signatures, but if performance is the only goal then batch verification techniques similar results, and exist for mny signature schemes, including Schnorr.  There are clear advantages to reducing interactiveness in threshold and multi-signaturtes, but parachains can always provide these on Polkadot.  Importantly, there are numerous weaknesses in all known curves that support pairings, but the single most damning weakness is the pairing itself.  
$$ e : G_1 \times G_2 \to G_T $$
In essence, we use elliptic curves in the first palce because they insulate us somewhat from mathematicians ever advancing understanding of number theory.  Yet, any known pairing maps into a group $G_T$ that re-exposes us, so attacks based on index-calculus, etc. improve more quickly.  As a real world example, there were weaknesses found in BN curve of the sort used by ZCash during development, so after launch they needed to develop and migrate to a [new curve](https://z.cash/blog/new-snark-curve/).  We expect this to happen again for roughly the same reasons that RSA key sizes increase slowly over time.


## Nominator keys

Any certificate format should work for nominator keys, but some certificate schemes provide more flexibility, while others save space.  We do not require much flexibility per se, but these certificates must live inside the staked account, and habe some associated data:

 - block height when staked,
 - unstaking block height, if unstaking, and
 - permissions, like block production, validation, and validator operator.

We could save some space by using implicit certificates to issue nominator keys, as implemented in [`schnorr-dalek/src/cert.rs`](https://github.com/w3f/schnorr-dalek/blob/master/src/cert.rs#L181).  In other words, an accounts nominator key could be defined by an additional 32 bytes attached to the account, along with any associated data.

We need to hold a conversation about (a) what form this associated data should take, and (b) if the space savings are worth the complexity of an implicit certificates scheme, mostly [reviewing the literature](https://github.com/w3f/schnorr-dalek/issues/4).  

We clearly need non-implicit certificates for non-owning nominators.  As a result, we might actually reduce the code complexity by not using implicit certificates in the nomination process.  We might then achieve better code reuse by not using implicit certificates anywhere. 

In any case, we need a conversation about the certificate schemes delegating from staked account keys to nominator keys and delegating from nominator keys to session keys.


## Session keys

A session public key should consist of roughly three public keys: 

 - Ristretto Schnorr public key (32 bytes public keys, 64 byte signatures, 96 byte VRFs) - We issue this from the nominator keys acting as validator operators.  We might use an implicit certificate but doing so either restricts us to one validator operator, or else increases code complexity and forces a primary validator operator.  Implicit certificates also make session key records impossible to authenticate without the nominator account, but this sounds desirable.  
 
 - Small curve of BLS12-381 (48 byte public keys, 96 byte signatures) - Aggregated signatures in which many signers sign the same message, as in GRANDPA, verify can faster when using this key.  Actual signatures are slower than the opposite orientation, and non-constant time extension field arithmetic makes them even slower, or more risky.

 - Big curve of BLS12-381 (96 bytes public keys, 48 byte signatures) - Aggregated signatures in which we verify many messages by the same signer verify considerably faster when using this key.  We might use these for block production VRFs because they require non-winner VRF proofs sometimes.  We also expect faster aggregate verification from these when signer sets get repeated frequently. 

A session public key record has a prefix consisting of the above three keys, along with a certificate from the validator operator on the Ristretto Schnorr public key.  We follow this prefix with a first signature block consisting two BLS signatures on the prefix, one by each the BLS keys.  We close the session public key record with a second signature block consisting of a Ristretto Schnorr signature on both the prefix and first signature block.  In this way, we may rotate our BLS12-381 keys without rotating our Ristretto Schnorr public key.



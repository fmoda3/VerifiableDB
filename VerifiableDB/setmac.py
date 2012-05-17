#!/usr/bin/env python
#
# Scheme for MACing sets from problem set 4-1
#
# Author: Madars Virza <madars@mit.edu> (c) 2012
#

import hashlib
import hmac
import os

HASH_FN = hashlib.sha256
MACLEN = 256//8

def H(key, s):
    """Returns digest of HMAC(key, s). Wrapped for improved
    readability."""
    return hmac.new(str(key), str(s), HASH_FN).digest()

def kvhash(key, k, v):
    """Returns value for repr(key)/repr(value) pair that should be
    computationally hard to forge. For real-world usage one must check
    that repr is collision-free for key/value pairs used."""
    return H(key, '%s|%s' % (H(key, repr(k)), H(key, repr(v))))

def xor_hashes(a, b):
    """Returns XOR of two hashes"""
    assert(len(a) == len(b))
    
    return "".join(chr(ord(x) ^ ord(y)) for (x, y) in zip(a, b))

def rand(k=32):
    """Returns k random bytes suitable for cryptographical purposes."""
    return os.urandom(k)

empty_compressed_MAC = chr(0) * MACLEN

def compress(key2, d):
    """``Compresses'' dictionary into a single hash value, that, when
    encrypted with a CCA2 secure scheme will yield unforgeable MACing
    scheme for dictionaries (see proof in our paper)."""
    r = empty_compressed_MAC
    for k, v in d.iteritems():
        r = xor_hashes(r, kvhash(key2, k, v))
    
    return r

def good_format(mac):
    assert(len(mac) == 2)
    assert(len(mac[0].decode("hex")) == MACLEN)
    assert(len(mac[1].decode("hex")) == MACLEN)
    return True

def extract_compressed_MAC(key1, mac):
    """Extracts compressed MAC from signature."""
    assert(good_format(mac))
    assert(good_format(mac))
    r, e = mac[0].decode("hex"), mac[1].decode("hex")
    c = xor_hashes(H(key1, r), e)
    return c

def marshall_MAC(mac):
    return mac[0] + "|" + mac[1]
    
def unmarshall_MAC(v):
    mac = v.split("|", 1)
    assert(good_format(mac))
    return mac

def encrypt_compressed_MAC(key1, c):
    """Encrypts compressed MAC with fresh randomness."""
    r = rand()
    return (r.encode("hex"), xor_hashes(H(key1, r), c).encode("hex"))    

def sign(key1, key2, d):
    """Creates a MAC for two sets."""
    c = compress(key2, d)
    return encrypt_compressed_MAC(key1, c)

def verify(key1, key2, d, mac):
    """Returns True iff ``mac'' is a valid MAC for dictionary d."""
    return extract_compressed_MAC(key1, c) == compress(key2, d)

def union(key1, mac1, mac2):
    """Returns MAC of union of two sets."""
    c1 = extract_compressed_MAC(key1, mac1)
    c2 = extract_compressed_MAC(key2, mac1)
    c = xor_hashes(c1, c2)
    
    return encrypt_compressed_MAC(key1, c)
    
# one could also implement remove for completeness, but it is not
# required for our application.


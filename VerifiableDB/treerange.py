#!/usr/bin/env python
#
# Author: Madars Virza <madars@mit.edu> (c) 2012
#

import balancedtree
import setmac
from django.db import models

class VerifiableTreeNode(balancedtree.BalancedTreeNode):
    def __init__(self, row_id, tree):
        c = tree.conn.cursor()
        c.execute("SELECT left, right, row_key, mac FROM %s WHERE row_id = ?" % tree.table_name, (row_id,))
        data = c.fetchone()
        c.close()
        
        left_id, right_id, self.row_key, self.mac = data
        self.mac = setmac.unmarshall_MAC(self.mac) if "|" in self.mac else None
        
        super(VerifiableTreeNode, self).__init__((self.row_key, row_id), row_id)
        
        # constructor overwrote our left and right
        self.left_id = left_id if left_id != -1 else None
        self.right_id = right_id if right_id != -1 else None
        
        self.tree = tree
        
        tree.cache[row_id] = self
    
    def get_left(self):
        if self.left_id:
            if self.left_id in self.tree.cache:
                return self.tree.cache[self.left_id]
            else:
                return VerifiableTreeNode(self.left_id, self.tree)
        else:
            return None

    def get_right(self):
        if self.right_id:
            if self.right_id in self.tree.cache:
                return self.tree.cache[self.right_id]
            else:
                return VerifiableTreeNode(self.right_id, self.tree)
        else:
            return None

    def set_left(self, node):
        if node:
            self.left_id = node.value
        else:
            self.left_id = None

    def set_right(self, node):
        if node:
            self.right_id = node.value
        else:
            self.right_id = None
    
    left = property(get_left, set_left)
    right = property(get_right, set_right)

    def verify(self):
        """Verifies that the MAC stored in this node is correct,
        assuming that left/right have correct MACs; also verifies the
        BST property."""
        mac = setmac.compress(self.tree.key2, {self.value: self.row_key})
        
        if self.left:
            assert(self.left.key < self.key)
            mac = setmac.xor_hashes(mac, setmac.extract_compressed_MAC(self.tree.key1, self.left.mac))
            
        if self.right:
            assert(not (self.right.key < self.key))
            mac = setmac.xor_hashes(mac, setmac.extract_compressed_MAC(self.tree.key1, self.right.mac))

        assert(setmac.extract_compressed_MAC(self.tree.key1, self.mac) == mac)

    def update_hook(self):
        """Rehashes child nodes."""
        mac = setmac.compress(self.tree.key2, {self.value: self.row_key})

        if self.left:
            mac = setmac.xor_hashes(mac, setmac.extract_compressed_MAC(self.tree.key1, self.left.mac))
            
        if self.right:
            mac = setmac.xor_hashes(mac, setmac.extract_compressed_MAC(self.tree.key1, self.right.mac))

        self.mac = setmac.encrypt_compressed_MAC(self.tree.key1, mac)

        left_id = self.left_id if self.left_id else -1
        right_id = self.right_id if self.right_id else -1

        c = self.tree.local_conn.cursor()
        c.execute("UPDATE %s SET left = ?, right = ?, mac = ? WHERE row_id = ?" % self.tree.table_name,
                  (left_id, right_id,
                   setmac.marshall_MAC(self.mac), self.value))
        self.tree.conn.commit()
        #self.tree.transaction.commit_unless_managed()
        c.close()
        

class VerifiableTree(balancedtree.BalancedTree):
    def __init__(self, table_name, field_name, type_name, conn, local_conn, transaction):
        self.table_name = '__verifiable_tree__%s__%s' % (table_name, field_name)
        self.field_name = field_name
        self.type_name = type_name
        self.conn = local_conn
        self.local_conn = local_conn
        self.cache = {}
        self.transaction = transaction

        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS %s
                     (left INTEGER,
                     right INTEGER,
                     row_id INTEGER,
                     row_key %s,
                     mac VARCHAR(100))""" % (self.table_name, self.type_name))
        self.conn.commit()
        #transaction.commit_unless_managed()

        def VTNFactory(key, value):
            c = self.conn.cursor()
            c.execute("SELECT COUNT(*) FROM %s WHERE row_id = ?" % self.table_name, (value,))
            data = c.fetchone()
            if not data[0]:
                c.execute("INSERT INTO %s (row_id, left, right, mac, row_key) VALUES (?, ?, ?, ?, ?)" % self.table_name,
                          (value, -1, -1, "empty-before-init", key))
                self.conn.commit()
                #transaction.commit_unless_managed()
            c.close()
             
            node = VerifiableTreeNode(value, self)
            node.update_hook() # update our MAC
            return node
        
        self.vtnfactory = VTNFactory

        super(VerifiableTree, self).__init__(VTNFactory)

        c = self.local_conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS verifiable_trees
                     (table_name VARCHAR(64) PRIMARY KEY,
                     key1 CHAR(32),
                     key2 CHAR(32),
                     key3 CHAR(32),
                     root_id INTEGER,
                     counter INTEGER,
                     root_hash VARCHAR(1024))""")
        self.local_conn.commit()
        
        c.execute("""SELECT key1, key2, key3, root_id, counter, root_hash
                     FROM verifiable_trees WHERE table_name = ?""", (self.table_name,))
        data = c.fetchone()
        if data:
            self.key1, self.key2, self.key3, root_id, self.counter, self.root_hash = data
        else:
            self.key1 = setmac.rand(32).encode("hex")
            self.key2 = setmac.rand(32).encode("hex")
            self.key3 = setmac.rand(32).encode("hex")
            root_id = -1
            self.counter = 1
            self.root = None
            self.recompute_root_hash()
            c.execute("""INSERT INTO verifiable_trees
                         (table_name,
                         key1,
                         key2,
                         key3,
                         root_id,
                         counter,
                         root_hash) VALUES (?, ?, ?, ?, ?, ?, ?)""", (self.table_name, self.key1, self.key2, self. key3, root_id, self.counter, self.root_hash))
            self.local_conn.commit()
        
        c.close()
        
        if root_id != -1:
            self.root = VerifiableTreeNode(root_id, self)

        self.check_root()

    def check_root(self):
        computed_hash = setmac.kvhash(self.key3, self.counter, None if not self.root else self.root.mac).encode("hex")
        assert(computed_hash == self.root_hash)

    def recompute_root_hash(self):
        self.root_hash = setmac.kvhash(self.key3, self.counter, None if not self.root else self.root.mac).encode("hex")

    def bump_root(self):
        self.counter += 1
        self.recompute_root_hash()

        root_id = self.root.value if self.root else -1

        c = self.local_conn.cursor()
        c.execute("UPDATE verifiable_trees SET root_id = ?, counter = ?, root_hash = ? WHERE table_name = ?", (root_id, self.counter, self.root_hash, self.table_name))
        self.local_conn.commit()
        c.close()

    def insert(self, row):
        self.check_root()
        super(VerifiableTree, self).insert(getattr(row, self.field_name), row.id)
        self.bump_root()
        
    def delete(self, row):
        self.check_root()

        c = self.conn.cursor()
        c.execute("SELECT row_key FROM %s WHERE row_id = ?" % self.table_name, (row.id,))
        (row_key,) = c.fetchone()
        self.conn.commit()
        #transaction.commit_unless_managed()        
        c.close()        
        
        super(VerifiableTree, self).delete((row_key, row.id))

        c = self.conn.cursor()
        c.execute("DELETE FROM %s WHERE row_id = ?" % self.table_name, (row.id,))
        self.conn.commit()
        #transaction.commit_unless_managed()        
        c.close()

        self.bump_root()

    def update(self, row):
        self.delete(row)
        self.insert(row)

    def verify(self, resultset, rmin, rmax, include_rmin=True, include_rmax=True):
        self.check_root()

        compressed_value = self.range_compressed_MAC(rmin, rmax, include_rmin, include_rmax)
        obtained_value = setmac.compress(self.key2, dict([(row.id, getattr(row, self.field_name)) for row in resultset]))
        return compressed_value == obtained_value
    
    def range_compressed_MAC(self, rmin, rmax, include_rmin=True, include_rmax=True):
        """Get compressed MAC for a range, verifying elements past the
        end of range."""

        if not self.root:
            return setmac.empty_compressed_MAC
        
        m_all = setmac.extract_compressed_MAC(self.key1, self.root.mac)
        
        if rmin:
            m_left = setmac.empty_compressed_MAC
            # invariant: after each iteration we still need to search
            # in t for the least value satisfying rmin constraint
            
            t = self.root
            
            while t:
                t.verify()

                if t.row_key < rmin or (t.row_key == rmin and not include_rmin):
                    # neither t nor t.left need to be included in the
                    # results, min satisfying is in t.right
                    t = t.right
                else:
                    # t and t.right needs to be included in the
                    # results. min satisfying is in t.left
                    m_left = setmac.xor_hashes(m_left, setmac.extract_compressed_MAC(self.key1, t.mac))
                    if t.left:
                        m_left = setmac.xor_hashes(m_left, setmac.extract_compressed_MAC(self.key1, t.left.mac))

                    t = t.left
        else:
            m_left = m_all

        if rmax:
            m_right = setmac.empty_compressed_MAC
            # invariant: after each iteration we still need to search
            # in t for the greatest value satisfying rmax constraint
            
            t = self.root
            
            while t:
                t.verify()

                if t.row_key > rmax or (t.row_key == rmax and not include_rmax):
                    # neither t nor t.right need to be included in the
                    # results, max satisfying is in t.left
                    t = t.left
                else:
                    # t and t.left needs to be included in the
                    # results. max satisfying is in t.right
                    m_right = setmac.xor_hashes(m_right, setmac.extract_compressed_MAC(self.key1, t.mac))
                    if t.right:
                        m_right = setmac.xor_hashes(m_right, setmac.extract_compressed_MAC(self.key1, t.right.mac))
                    t = t.right
        else:
            m_right = m_all
        
        return setmac.xor_hashes(m_all, setmac.xor_hashes(m_left, m_right))

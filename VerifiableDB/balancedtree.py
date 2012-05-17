#!/usr/bin/env python
#
# Implementation of balanced trees with associated tests
#
# Author: Madars Virza <madars@mit.edu> (c) 2012
#

class BalancedTree(object):
    """
    Implementation of a balanced binary search tree.
    
    Current implementation: AVL tree from J.A. Storer's ``Introduction
    to Data Structures and Algorithms''.
    
    To ease augmenting after each batch of rebalancing updates to
    node.{left,right} a special method node.update_hook is called, so
    augmented structure can be correctly populated.
    """
    def __init__(self, node_factory):
        """Initializes the tree to empty one."""
        self.root = None
        self.node_factory = node_factory

    def insert(self, key, value):
        """Inserts a key/value pair in the tree."""
        node = self.node_factory(key, value)

        if self.root:
            self.root = self.root.insert(node)
        else:
            self.root = node
    
    def delete(self, key):
        """Deletes the specified node from tree and returns it."""
        assert(self.root)
        self.root, node = self.root.delete(key)
        return node

    def find(self, key):
        """Returns the specified node from tree or None if the
        node is not present."""
        if root:
            return self.root.find(key)
        else:
            return None

class BalancedTreeNode(object):
    def __init__(self, key, value):
        """Initializes node. Doesn't call update_hook."""
        self.key, self.value = key, value
        self.left, self.right = None, None
        self.height = 1

    def visit_hook(self):
        """A hook function called on every recursive call of
        find/insert/delete just after entering the node. Not called on
        insert."""
        pass

    def update_hook(self):
        """A hook function called by rotate operations after any batch
        of updates to self.{left,right} on node or any of its
        descendants. It is guarranteed that update_hook of a node will
        be called after all update_hook calls of its descendants.

        Not called on nodes that are removed from the tree, nor on
        insert."""
        pass

    def find(self, key):
        """Retrieves the specified node from the tree."""
        self.visit_hook()

        if node.key == self.key:
            return self
        elif node.key < self.key:
            return self.left.find(key)
        else:
            return self.right.find(key)

    def insert(self, node):
        """Inserts the specified node into this subtree."""
        self.visit_hook()
        
        if node.key < self.key:
            self.left = self.left.insert(node) if self.left else node
        else:
            self.right = self.right.insert(node) if self.right else node
        return self.balance()

    def delete(self, key):
        """Deletes the item with the specified key from this subtree
        and returns pair (newroot, deleted_item)"""
        self.visit_hook()
        
        if key < self.key:
            assert(self.left)
            self.left, node = self.left.delete(key)
            return (self.balance(), node)
        elif self.key < key:
            assert(self.right)
            self.right, node = self.right.delete(key)
            return (self.balance(), node)
        else:
            # in either of two cases below we return a balanced tree
            if not self.left:
                newroot = self.right
                self.right = None
                
                return (newroot, self)
            if not self.right:
                newroot = self.left
                self.left = None

                return (newroot, self)

            # |left.height-right.height| <= 1 if we remove min from
            # right, then |left.height-right'.height| <=2 and
            # balancing conditions are met. So balance()'s on the way
            # to root will be able to properly rebalance the tree.

            upper_bound = self.right
            
            while upper_bound.left:
                upper_bound = upper_bound.left
                
            newright, newself = self.right.delete(upper_bound.key)
            newself.left = self.left
            newself.right = newright
            
            self.left = None
            self.right = None
            return (newself.balance(), self)

    def lheight(self):
        """Returns height of left subtree."""
        return self.left.height if self.left else 0

    def rheight(self):
        """Returns height of right subtree."""
        return self.right.height if self.right else 0

    def update_height(self):
        """Recomputes height."""
        self.height = 1 + max(self.lheight(), self.rheight())

    def balance(self):
        """Balances tree rooted at this node, assuming that height
        difference for the root is at most +-2 and that height
        difference for all descendants are +-1. Returns the new root.
        
        Calls update_hook if no balancing is necessary, because balance
        will be used recursively in insert/delete."""

        # pretty ASCII diagrams adapted from Storer's book
        
        if self.lheight() > 1 + self.rheight():
            if self.left.lheight() < self.left.rheight():
                #
                #  subcase: b is right-heavy:
                # 
                #        a                a
                #       / \              / \
                #      b   T(h)         c   T(h)
                #     / \      =>      / \
                #   X(h) c            b   Z  --+
                #       / \          / \       |
                #  +-- Y   Z --+  X(h)  Y  --+ |
                #  |           |             | |
                #  |           |             | |
                #  |           |             | |
                # in each tree one is h and one is h or h-1
                #
                self.left = self.left.rotate_left()
            #
            # now b is left-heavy:
            #
            #     a             b
            #    / \           / \
            #   b   Z(h)  =>  X   a
            #  / \               / \
            # X   Y             Y   Z(h)
            #
            # If subcase didn't apply X,Y is h,h-1 or h,h (in this
            # order) and balance is preserved.
            #
            # If subcase applied then X,Y is h+1,h or h+1,h-1 (in this
            # order); the balance is still preserved.
            #
            return self.rotate_right()
        elif self.rheight() > 1 + self.lheight():
            # (symmetric; drawing diagrams is too tedious)
            if self.right.rheight() < self.right.lheight():
                self.right = self.right.rotate_right()
            return self.rotate_left()
        else:
            # both are called in rotation
            self.update_height()
            self.update_hook()
            return self

    def rotate_left(self):
        """
        Performs a left rotation and returns the new root:
        
           a             b
          / \           / \
         X   b    =>   a   Z   (X < a <= Y < b <= Z)
            / \       / \ 
           Y   Z     X   Y
        """
        assert(self.right)
        a, b = self, self.right
        a.right, b.left = b.left, a

        a.update_height(); a.update_hook()
        b.update_height(); b.update_hook()
        return b

    def rotate_right(self):
        """
        Performs a right rotation and returns the new root:
        
            b            a
           / \          / \
          a   Z   =>   X   b   (X < a <= Y < b <= Z)
         / \              / \
        X   Y            Y   Z
        """
        assert(self.left)
        a, b = self.left, self
        a.right, b.left = b, a.right

        b.update_height(); b.update_hook()
        a.update_height(); a.update_hook()
        return a

def xor_test():
    """Performs a simple XOR-based test."""
    import random
    
    class XORTestNode(BalancedTreeNode):
        """Test for child hooks: maintains XOR of all numbers in this subtree."""
        def __init__(self, key, value):
            """Initializes node, setting xor to value and size to 1,
            which corresponds to subtree consisting just of the root."""
            super(XORTestNode, self).__init__(key, value)
            self.xor = value
            self.size = 1
        
        def update_hook(self):
            """Updates node, by recalculating size and XOR."""
            self.xor = self.value
            self.size = 1
            if self.left:
                self.xor ^= self.left.xor
                self.size += self.left.size
            if self.right:
                self.xor ^= self.right.xor
                self.size += self.right.size

    def pretty(node, prefix='', you='', seen=[]):
        """Pretty prints XORTestNodes; provides cycle detection which was
        used for debugging earlier implementations."""
        if not node:
            print '%snil' % you
        elif (node.key, node.value) in seen:
            print '%s%s: %s XOR=%s (cycle!)' % (you, node.key, node.value, node.xor)
        else:
            print '%s%s: %s XOR=%s' % (you, node.key, node.value, node.xor)
            pretty(node.left, prefix+'  | ', prefix+'  +-', seen+[(node.key, node.value)])
            pretty(node.right, prefix+'    ', prefix+'  \\-', seen+[(node.key, node.value)])

    N = 1<<14
    t = BalancedTree(XORTestNode)
    arr = [random.randint(0, N) for i in xrange(N)]
    allxor = 0
    
    for i,k in enumerate(arr):
        r = random.randint(0, 1<<31)
        
        t.insert(k, r)
        allxor ^= r

    assert(t.root.size == N)
    print "Built a tree with height=%d, size=%d" % (t.root.height, t.root.size)
    
    arr2 = []
    while t.root:
        assert(allxor == t.root.xor)
        assert(t.root.size == N)
        
        m = t.root
        while m.left:
            m = m.left
        node = t.delete(m.key)
        
        arr2.append(node.key)
        allxor ^= node.value
        N -= 1

    assert(sorted(arr) == arr2)
    
    print "All tests passed"

if __name__ == '__main__':
    xor_test()


    

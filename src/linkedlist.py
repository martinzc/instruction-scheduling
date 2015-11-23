class Node:
    def __init__(self, val):
        self.val = val
        self.prev = None
        self.next = None


class LinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def append(self, val):
        self.size += 1
        if self.head is None:
            self.head = Node(val)
            self.tail = self.head
        else:
            node = Node(val)
            node.prev = self.tail
            self.tail.next = node
            self.tail = node

    def insert_before(self, node, val):
        new_node = Node(val)
        if self.head == node:
            self.head = new_node
            self.head.next = node
            node.prev = self.head
            return

        prev_node = node.prev
        prev_node.next = new_node
        new_node.prev = prev_node
        new_node.next = node
        node.prev = new_node

    def delete(self, node):
        if self.head == node and self.tail == node:
            self.head = None
            self.tail = None
        elif self.head == node:
            node.next.prev = None
            self.head = node.next
        elif self.tail == node:
            node.prev.next = None
            self.tail = node.prev
        else:
            node.prev.next = node.next
            node.next.prev = node.prev

        node.prev = None
        node.next = None
from collections import deque
from heapq import heappop, heappush

GRAPH = '''digraph g {{
    {}
}}
'''


class Scheduler():
    def __init__(self, operations, src_regs):
        self.operations = operations
        self.vr_name = 0
        self.sr_to_vr = dict.fromkeys(src_regs)
        self.last_use = dict.fromkeys(src_regs)
        self.max_live = 0
        self.curr_live = 0
        self.graph = {}
        self.delays = {'load': 5, 'loadI': 1, 'store': 5, 'add': 1, 'sub': 1, 'mult': 3,
                       'lshift': 1, 'rshift': 1, 'output': 1, 'nop': 1}
        self.f = {0: [], 1: []}
        self.illegal_opcode = {0: {'mult'}, 1: {'load', 'store'}}
        self.schedule = {}
        self.out_degrees = None
        self.reverse_graph = {}

    def rename_regs(self):
        node = self.operations.tail
        while node is not None:
            operation = node.val
            self.max_live = max(self.max_live, self.curr_live)

            if operation.opcode == 'output':
                node = node.prev
                continue

            if operation.opcode == 'store':
                self._update(operation.op3, operation.idx)
                self._update(operation.op1, operation.idx)
            else:
                self._update(operation.op3, operation.idx)
                if operation.op3:
                    self.sr_to_vr[operation.op3.sr] = None
                    self.last_use[operation.op3.sr] = None
                    self.curr_live -= 1

                self._update(operation.op1, operation.idx)
                self._update(operation.op2, operation.idx)

            node = node.prev

    def _update(self, op, idx):
        if op is None or op.sr.isdigit():
            return

        if self.sr_to_vr[op.sr] is None:
            self.sr_to_vr[op.sr] = 'r' + str(self.vr_name)
            self.vr_name += 1
            self.curr_live += 1

        op.vr = self.sr_to_vr[op.sr]
        op.next_use = self.last_use[op.sr]
        self.last_use[op.sr] = idx

    def build_dependence_graph(self):
        node = self.operations.head
        sinks = {'store': None, 'output': None, 'load': None}
        while node is not None:
            dependence = self.get_dependence(node, sinks)
            self.graph[node.val] = dependence
            if node.val.opcode == 'store':
                sinks['store'] = node.val
            elif node.val.opcode == 'output':
                sinks['output'] = node.val
            elif node.val.opcode == 'load':
                sinks['load'] = node.val

            if node.val.op3:
                sinks[node.val.op3.vr] = node.val
            node = node.next

        self.init_priority()

    def get_dependence(self, node, sinks):
        opcode = node.val.opcode
        op1 = node.val.op1
        op2 = node.val.op2
        op3 = node.val.op3

        dependence = set()
        if opcode == 'load' and sinks['store'] is not None:
            dependence.add(sinks['store'])
        elif opcode == 'output':
            if sinks['store'] is not None:
                dependence.add(sinks['store'])
            elif sinks['output'] is not None:
                dependence.add(sinks['output'])
        elif opcode == 'store':
            dependence.add(sinks[op3.vr])
            if sinks['store'] is not None:
                dependence.add(sinks['store'])
            elif sinks['output'] is not None:
                dependence.add(sinks['output'])
            elif sinks['load'] is not None:
                dependence.add(sinks['load'])

        if op1 and op1.sr.isdigit() is False and op1.vr in sinks:
            dependence.add(sinks[op1.vr])

        if op2 and op2.sr.isdigit() is False and op2.vr in sinks:
            dependence.add(sinks[op2.vr])

        return dependence

    def to_graph(self):
        nodes = ['{0} [label=\"{0} {1} Priority: {2}\"]'.format(operation.idx, str(operation), operation.priority) for
                 operation in self.graph.keys()]
        str_nodes = ';\n    '.join(nodes)

        edges = []
        for source, sinks in self.graph.iteritems():
            for sink in sinks:
                edges.append('{0}->{1}'.format(source.idx, sink.idx))

        str_edges = ';\n    '.join(edges)
        return GRAPH.format('{0};\n    {1};'.format(str_nodes, str_edges))

    def init_priority(self):
        in_degrees = {node: 0 for node in self.graph.keys()}
        self.out_degrees = {node: len(neighbors) for node, neighbors in self.graph.iteritems()}
        self.reverse_graph = {node: set() for node in self.graph.keys()}
        for node, neighbors in self.graph.iteritems():
            for neighbor in neighbors:
                in_degrees[neighbor] += 1
                self.reverse_graph[neighbor].add(node)

        dq = deque()
        for node, count in in_degrees.iteritems():
            if count == 0:
                node.priority = self.delays[node.opcode]
                dq.append(node)

        while len(dq) > 0:
            operation = dq.pop()
            neighbors = self.graph[operation]

            for neighbor in neighbors:
                if in_degrees[neighbor] > 0:
                    if neighbor.priority is None:
                        neighbor.priority = self.delays[neighbor.opcode] + operation.priority
                    else:
                        neighbor.priority = max(neighbor.priority, self.delays[neighbor.opcode] + operation.priority)

                    in_degrees[neighbor] -= 1
                    if in_degrees[neighbor] == 0:
                        dq.append(neighbor)

    def perform(self):
        cycle = 1
        ready = []
        for node, count in self.out_degrees.iteritems():
            if count == 0:
                heappush(ready, node)

        active = []

        while len(ready) > 0 or len(active) > 0:
            for idx in reversed(range(2)):
                operation = self.get_operation(idx, ready)
                if operation is None:
                    self.f[idx].append('nop')
                else:
                    self.f[idx].append(str(operation))
                    self.schedule[operation] = cycle
                    active.append(operation)

            cycle += 1

            to_delete = set()
            for operation in active:
                if self.schedule[operation] + self.delays[operation.opcode] <= cycle:
                    to_delete.add(operation)
                    successors = self.get_ready_successors(operation)
                    for successor in successors:
                        heappush(ready, successor)

            active = [operation for operation in active if operation not in to_delete]

        length = len(self.f[0])
        for i in range(length):
            print('[{0}; {1}]'.format(self.f[0][i], self.f[1][i]))

    def get_operation(self, idx, ready):
        temp = []
        result = None

        for i in range(len(ready)):
            operation = heappop(ready)
            if operation.opcode in self.illegal_opcode[idx]:
                temp.append(operation)
            else:
                result = operation
                break

        for operation in temp:
            heappush(ready, operation)

        return result

    def get_ready_successors(self, operation):
        result = []
        successors = self.reverse_graph[operation]
        for successor in successors:
            if self.out_degrees[successor] > 0:
                self.out_degrees[successor] -= 1
                if self.out_degrees[successor] == 0:
                    result.append(successor)

        return result
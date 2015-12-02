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
        self.vals = {}
        self.dependency_vals = {}

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
        loads = set()
        outputs = set()
        sinks = {'store': None, 'output': None, 'load': None}
        while node is not None:
            dependence = self.get_dependence(node, sinks, loads, outputs)
            self.graph[node.val] = dependence
            if node.val.opcode == 'store':
                sinks['store'] = node.val
            elif node.val.opcode == 'output':
                sinks['output'] = node.val
                outputs.add(node.val)
            elif node.val.opcode == 'load':
                sinks['load'] = node.val
                loads.add(node.val)

            if node.val.op3:
                self.track_reg(node.val)
                sinks[node.val.op3.vr] = node.val

            node = node.next

        self.init_priority()

    def track_reg(self, operation):
        opcode = operation.opcode
        op1 = operation.op1
        op2 = operation.op2
        op3 = operation.op3

        if opcode == 'loadI':
            self.vals[op3.vr] = op1.sr
        elif opcode == 'load':
            if op1.vr in self.vals:
                addr = self.vals[op1.vr]
                self.dependency_vals[operation] = addr
                if addr in self.vals:
                    self.vals[op3.vr] = self.vals[addr]
        elif opcode == 'store':
            if op3.vr in self.vals:
                addr = self.vals[op3.vr]
                self.dependency_vals[operation] = addr
                if op1.vr in self.vals:
                    self.vals[addr] = self.vals[op1.vr]
        elif opcode == 'add':
            if op1.vr in self.vals and op2.vr in self.vals:
                self.vals[op3.vr] = int(self.vals[op1.vr]) + int(self.vals[op2.vr])
        elif opcode == 'sub':
            if op1.vr in self.vals and op2.vr in self.vals:
                self.vals[op3.vr] = int(self.vals[op1.vr]) - int(self.vals[op2.vr])
        elif opcode == 'mult':
            if op1.vr in self.vals and op2.vr in self.vals:
                self.vals[op3.vr] = int(self.vals[op1.vr]) * int(self.vals[op2.vr])
        elif opcode == 'lshift':
            if op1.vr in self.vals and op2.vr in self.vals:
                self.vals[op3.vr] = int(self.vals[op1.vr]) << int(self.vals[op2.vr])
        elif opcode == 'rshift':
            if op1.vr in self.vals and op2.vr in self.vals:
                self.vals[op3.vr] = int(self.vals[op1.vr]) << int(self.vals[op2.vr])

    def is_dependence(self, addr1, addr2):
        addr1 = int(addr1)
        addr2 = int(addr2)
        if addr1 and addr2:
            return True if addr1 == addr2 else False

        return True

    def get_dependence(self, node, sinks, loads, outputs):
        opcode = node.val.opcode
        op1 = node.val.op1
        op2 = node.val.op2
        op3 = node.val.op3

        dependence = set()
        if opcode == 'load' and sinks['store'] is not None:
            # check store op3's value == load op1's value
            store_addr = self.vals[sinks['store'].op3.vr] if sinks['store'].op3.vr in self.vals else None
            load_op1 = self.vals[op1.vr] if op1.vr in self.vals else None
            if self.is_dependence(store_addr, load_op1):
                dependence.add(sinks['store'])
        elif opcode == 'output':
            if sinks['store'] is not None:
                # check store op3's value
                store_addr = self.vals[sinks['store'].op3.vr] if sinks['store'].op3.vr in self.vals else None
                if self.is_dependence(store_addr, op1.sr):
                    dependence.add(sinks['store'])
            if sinks['output'] is not None:
                dependence.add(sinks['output'])
        elif opcode == 'store':
            dependence.add(sinks[op3.vr])
            if sinks['store'] is not None:
                # check store op3's value == store op3's value
                store_addr1 = self.vals[sinks['store'].op3.vr] if sinks['store'].op3.vr in self.vals else None
                store_addr2 = self.vals[op3.vr] if op3.vr in self.vals else None
                if self.is_dependence(store_addr1, store_addr2):
                    dependence.add(sinks['store'])
            if sinks['output'] is not None:
                # check store op3's value == output op1
                store_addr = self.vals[op3.vr] if op3.vr in self.vals else None
                for output_op in outputs:
                    output_addr = output_op.op1.sr
                    if self.is_dependence(store_addr, output_addr):
                        dependence.add(output_op)
            if sinks['load'] is not None:
                # check store op3's value == load op1's value
                store_addr = self.vals[op3.vr] if op3.vr in self.vals else None
                for load_op in loads:
                    load_addr = self.vals[load_op.op1.vr] if load_op.op1.vr in self.vals else None
                    if self.is_dependence(store_addr, load_addr):
                        dependence.add(load_op)

        if op1 and op1.sr.isdigit() is False and op1.vr in sinks:
            dependence.add(sinks[op1.vr])

        if op2 and op2.sr.isdigit() is False and op2.vr in sinks:
            dependence.add(sinks[op2.vr])

        return dependence

    def to_graph(self):
        nodes = ['{0} [label=\"{0} {1} Priority: {2}\"]'.format(operation.idx, operation, operation.priority) for
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
                    self.f[idx].append(operation)
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
            f0 = self.f[0][i] if isinstance(self.f[0][i], str) else self.f[0][i].get_vr_str()
            f1 = self.f[1][i] if isinstance(self.f[1][i], str) else self.f[1][i].get_vr_str()
            print('[{0}; {1}]'.format(f0, f1))

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
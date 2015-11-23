class Scheduler():
    def __init__(self, operations, src_regs):
        self.operations = operations
        self.vr_name = 0
        self.sr_to_vr = dict.fromkeys(src_regs)
        self.last_use = dict.fromkeys(src_regs)
        self.max_live = 0
        self.curr_live = 0

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
        while node is not None:

            node = node.next
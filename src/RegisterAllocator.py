import copy

from ILOCOperation import ILOCOperand
from ILOCOperation import ILOCOperation


class RegisterAllocator:
    def __init__(self, operations, src_regs):
        self.operations = operations
        self.vr_name = 0
        self.sr_to_vr = dict.fromkeys(src_regs)
        self.last_use = dict.fromkeys(src_regs)
        self.vr_to_pr = {}
        self.max_live = 0
        self.curr_live = 0
        self.mem_addr = 32768
        self.spilled_vrs = {}
        self.vr_next_use = {}
        self.vr_initial_nodes = {}
        self.deleted_nodes = set()
        self.used_vrs = set()
        self.unavailable_vr = None
        self.clean_spilled_vr = {}
        self.reserved_pr = None

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
            self.vr_to_pr[self.sr_to_vr[op.sr]] = None
            self.vr_name += 1
            self.curr_live += 1

        op.vr = self.sr_to_vr[op.sr]
        op.next_use = self.last_use[op.sr]
        self.last_use[op.sr] = idx

    def alloc_regs(self, k):
        if self.max_live <= k:
            self.alloc_regs_without_spilling(k)
        else:
            self.alloc_regs_with_spilling(k)

    def alloc_regs_without_spilling(self, k):
        pr_stack = [None] * k
        node = self.operations.head
        while node is not None:
            operation = node.val
            if operation.opcode == 'output':
                node = node.next
                continue

            if operation.opcode == 'store':
                op1 = operation.op1
                if self.vr_to_pr[op1.vr] is None:
                    op1.pr = self._allocate_pr(pr_stack, op1.vr)
                else:
                    op1.pr = self.vr_to_pr[op1.vr]

                op3 = operation.op3
                if self.vr_to_pr[op3.vr] is None:
                    op3.pr = self._allocate_pr(pr_stack, op3.vr)
                else:
                    op3.pr = self.vr_to_pr[op3.vr]
            else:
                op1 = operation.op1
                if op1.sr.isdigit() is False and self.vr_to_pr[op1.vr] is None:
                    op1.pr = self._allocate_pr(pr_stack, op1.vr)
                elif op1.sr.isdigit() is False:
                    op1.pr = self.vr_to_pr[op1.vr]

                op2 = operation.op2
                if op2 and self.vr_to_pr[op2.vr] is None:
                    op2.pr = self._allocate_pr(pr_stack, op2.vr)
                elif op2:
                    op2.pr = self.vr_to_pr[op2.vr]

                if op1.sr.isdigit() is False and op1.next_use is None:
                    self._free_pr(pr_stack, op1.vr)

                if op2 and op2.next_use is None:
                    self._free_pr(pr_stack, op2.vr)

                op3 = operation.op3
                op3.pr = self._allocate_pr(pr_stack, op3.vr)

            node = node.next

    def alloc_regs_with_spilling(self, k):
        self.reserved_pr = 'r' + str(k - 1)
        pr_stack = [None] * (k - 1)
        node = self.operations.head
        while node is not None:
            operation = node.val
            if operation.opcode == 'output':
                node = node.next
                continue

            if operation.opcode == 'store':
                op1 = operation.op1
                self.vr_next_use[op1.vr] = op1.next_use
                self.unavailable_vr = None
                if self.vr_to_pr[op1.vr] is None:
                    op1.pr = self._allocate_pr_with_spilling(pr_stack, op1.vr, node)
                    self._restore_spilled_vr(op1.vr, op1.pr, node)
                else:
                    op1.pr = self.vr_to_pr[op1.vr]
                self.unavailable_vr = op1.vr
                self.used_vrs.add(op1.vr)

                op3 = operation.op3
                self.vr_next_use[op3.vr] = op3.next_use
                if self.vr_to_pr[op3.vr] is None:
                    op3.pr = self._allocate_pr_with_spilling(pr_stack, op3.vr, node)
                    self._restore_spilled_vr(op3.vr, op3.pr, node)
                else:
                    op3.pr = self.vr_to_pr[op3.vr]
                self.used_vrs.add(op3.vr)

                if op1.next_use is None:
                    self._free_pr(pr_stack, op1.vr)

                if op3.next_use is None:
                    self._free_pr(pr_stack, op3.vr)
            else:
                self.unavailable_vr = None
                op1 = operation.op1
                if op1.sr.isdigit() is False:
                    self.vr_next_use[op1.vr] = op1.next_use
                    if self.vr_to_pr[op1.vr] is None:
                        op1.pr = self._allocate_pr_with_spilling(pr_stack, op1.vr, node)
                        self._restore_spilled_vr(op1.vr, op1.pr, node)
                    else:
                        op1.pr = self.vr_to_pr[op1.vr]
                    self.unavailable_vr = op1.vr
                    self.used_vrs.add(op1.vr)

                op2 = operation.op2
                if op2:
                    self.vr_next_use[op2.vr] = op2.next_use
                    if self.vr_to_pr[op2.vr] is None:
                        op2.pr = self._allocate_pr_with_spilling(pr_stack, op2.vr, node)
                        self._restore_spilled_vr(op2.vr, op2.pr, node)
                    else:
                        op2.pr = self.vr_to_pr[op2.vr]
                    self.used_vrs.add(op2.vr)

                if op1.sr.isdigit() is False and op1.next_use is None:
                    self._free_pr(pr_stack, op1.vr)

                if op2 and op2.next_use is None:
                    self._free_pr(pr_stack, op2.vr)

                self.unavailable_vr = None
                op3 = operation.op3
                self.vr_next_use[op3.vr] = op3.next_use
                self.vr_initial_nodes[op3.vr] = node
                op3.pr = self._allocate_pr_with_spilling(pr_stack, op3.vr, node)
                if op3.next_use is None:
                    self._free_pr(pr_stack, op3.vr)

                if op3.vr in self.used_vrs:
                    self.used_vrs.remove(op3.vr)

                if op3.vr in self.clean_spilled_vr:
                    self.clean_spilled_vr.pop(op3.vr)

            node = node.next

        for node in self.deleted_nodes:
            self.operations.delete(node)

    def _allocate_pr(self, pr_stack, vr):
        for i in range(0, len(pr_stack)):
            if pr_stack[i] is None:
                pr_stack[i] = vr
                pr_name = 'r' + str(i)
                self.vr_to_pr[vr] = pr_name
                return pr_name

        return None

    def _free_pr(self, pr_stack, vr):
        for i in range(0, len(pr_stack)):
            if pr_stack[i] == vr:
                pr_stack[i] = None
                self.vr_to_pr[vr] = None
                return

    def _allocate_pr_with_spilling(self, pr_stack, vr, node):
        for i in range(0, len(pr_stack)):
            if pr_stack[i] is None:
                pr_stack[i] = vr
                pr_name = 'r' + str(i)
                self.vr_to_pr[vr] = pr_name
                return pr_name

        idx = self._spill_vr(pr_stack, node)
        pr_stack[idx] = vr
        pr_name = 'r' + str(idx)
        self.vr_to_pr[vr] = pr_name
        return pr_name

    def _spill_vr(self, pr_stack, node):
        vr = None
        idx = 0
        farthest_use = 0
        rematerialized_vrs = {}
        for i in range(0, len(pr_stack)):
            if pr_stack[i] in self.vr_initial_nodes:
                if self.vr_initial_nodes[pr_stack[i]].val.opcode == 'loadI':
                    rematerialized_vrs[pr_stack[i]] = i
        if len(rematerialized_vrs) > 0:
            for rematerialized_vr in rematerialized_vrs:
                next_use = self.vr_next_use[rematerialized_vr]
                if next_use and next_use > farthest_use:
                    if self.unavailable_vr is None or rematerialized_vr != self.unavailable_vr:
                        farthest_use = next_use
                        idx = rematerialized_vrs[rematerialized_vr]
                        vr = rematerialized_vr
        if vr is None:
            for i in range(0, len(pr_stack)):
                next_use = self.vr_next_use[pr_stack[i]]
                if next_use and next_use > farthest_use:
                    if self.unavailable_vr is None or pr_stack[i] != self.unavailable_vr:
                        farthest_use = next_use
                        idx = i
                        vr = pr_stack[i]

        delete_node = self.vr_initial_nodes[vr]
        if delete_node.val.opcode == 'loadI':
            self.vr_to_pr[vr] = None
            self.spilled_vrs[vr] = (delete_node.val,)
            if vr not in self.used_vrs:
                self.deleted_nodes.add(delete_node)
                self._free_pr(pr_stack, vr)
        elif vr in self.clean_spilled_vr:
            addr = self.clean_spilled_vr[vr]
            op1 = ILOCOperand(sr=addr)
            op3 = ILOCOperand(pr=self.reserved_pr)
            load_operation1 = ILOCOperation(opcode='loadI', op1=op1, op3=op3)
            load_operation1.comment = '\t// restoring v{} => '.format(vr)
            load_operation2 = ILOCOperation(opcode='load', op1=op3, op3=ILOCOperand())
            load_operation2.comment = '\t// restoring v{} => '.format(vr)
            self.vr_to_pr[vr] = None
            self.spilled_vrs[vr] = load_operation1, load_operation2
        else:
            op1 = ILOCOperand(sr=str(self.mem_addr))
            op3 = ILOCOperand(pr=self.reserved_pr)
            store_operation = ILOCOperation(opcode='loadI', op1=op1, op3=op3)
            store_operation.comment = '\t// spilling v' + vr
            self.operations.insert_before(node, store_operation)
            op1 = ILOCOperand(pr=self.vr_to_pr[vr])
            store_operation = ILOCOperation(opcode='store', op1=op1, op3=op3)
            store_operation.comment = '\t// spilling v' + vr
            self.operations.insert_before(node, store_operation)

            op1 = ILOCOperand(sr=str(self.mem_addr))
            load_operation1 = ILOCOperation(opcode='loadI', op1=op1, op3=op3)
            load_operation1.comment = '\t// restoring v{} => '.format(vr)
            load_operation2 = ILOCOperation(opcode='load', op1=op3, op3=ILOCOperand())
            load_operation2.comment = '\t// restoring v{} => '.format(vr)
            self.vr_to_pr[vr] = None
            self.spilled_vrs[vr] = load_operation1, load_operation2
            self.clean_spilled_vr[vr] = str(self.mem_addr)
            self.mem_addr += 4

        return idx

    def _restore_spilled_vr(self, vr, pr, node):
        if vr in self.spilled_vrs:
            restore_operations = self.spilled_vrs[vr]
            if len(restore_operations) == 1:
                load_operation = copy.deepcopy(restore_operations[0])
                load_operation.op3.pr = pr
                load_operation.comment = '\t// rematerialized'
                self.operations.insert_before(node, load_operation)
            else:
                restore_operations[0].comment += 'p' + pr
                self.operations.insert_before(node, restore_operations[0])
                restore_operations[1].op3.pr = pr
                restore_operations[1].comment += 'p' + pr
                self.operations.insert_before(node, restore_operations[1])
            self.spilled_vrs.pop(vr)

    def print_vrs(self):
        node = self.operations.head
        while node is not None:
            operation = node.val
            print(operation.get_vr_str())
            node = node.next

    def print_prs(self):
        node = self.operations.head
        while node is not None:
            operation = node.val
            print(operation.get_pr_str())
            node = node.next
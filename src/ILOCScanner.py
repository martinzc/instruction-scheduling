from ILOCOperation import ILOCOperand
from ILOCOperation import ILOCOperation
from fsm import op_fsm, reg_fsm, int_fsm
from linkedlist import LinkedList


class ILOCScanner:
    def __init__(self):
        self.src_regs = set()

    def scan_file(self, file_name):
        operations = LinkedList()
        with open(file_name) as f:
            i = 0
            for line in f:
                operation = self._parse_line(line)
                if operation is not None:
                    operation.idx = i
                    i += 1

                    operations.append(operation)

        return operations, self.src_regs

    def _parse_line(self, line):
        opcode, i = self._parse_symbol(line, 0, op_fsm)
        if opcode == 'store' or opcode == 'load':
            return self._parse_mem_op(line, i, opcode)
        elif opcode == 'add' or opcode == 'sub' or opcode == 'mult' or opcode == 'lshift' or opcode == 'rshift':
            return self._parse_arith_op(line, i, opcode)
        elif opcode == 'loadI':
            return self._parse_loadi(line, i)
        elif opcode == 'output':
            return self._parse_output(line, i)
        else:  # nop
            return None

    @staticmethod
    def _parse_symbol(line, i, fsm):
        len_line = len(line)
        while i < len_line and (line[i] == ' ' or line[i] == '\t'):
            i += 1

        if i == len_line or line[i] == '/' or line[i] == '\n':
            return None, None

        prev_state = 0
        state = 0
        start = i
        while i < len_line and state != -1:
            prev_state = state
            state = fsm.next_state(state, line[i])
            i += 1

        if fsm.is_accept_state(state):
            return line[start:i], i
        elif fsm.is_accept_state(prev_state):
            return line[start:i - 1], i - 1
        else:
            raise ValueError('Illegal operation: {}.'.format(line))

    def _parse_mem_op(self, line, i, opcode):
        reg1, i = self._parse_symbol(line, i, reg_fsm)
        reg1 = self._delete_prefix_0_for_reg(reg1)
        self.src_regs.add(reg1)

        into, i = self._parse_symbol(line, i, op_fsm)
        if into != '=>':
            raise ValueError('Illegal operation: {}.'.format(line))

        reg2, i = self._parse_symbol(line, i, reg_fsm)
        reg2 = self._delete_prefix_0_for_reg(reg2)
        self.src_regs.add(reg2)

        op1 = ILOCOperand(sr=reg1)
        op3 = ILOCOperand(sr=reg2)
        return ILOCOperation(opcode=opcode, op1=op1, op3=op3)

    def _parse_arith_op(self, line, i, opcode):
        reg1, i = self._parse_symbol(line, i, reg_fsm)
        reg1 = self._delete_prefix_0_for_reg(reg1)
        self.src_regs.add(reg1)

        comma, i = self._parse_symbol(line, i, op_fsm)
        if comma != ',':
            raise ValueError('Illegal operation: {}.'.format(line))

        reg2, i = self._parse_symbol(line, i, reg_fsm)
        reg2 = self._delete_prefix_0_for_reg(reg2)
        self.src_regs.add(reg2)

        into, i = self._parse_symbol(line, i, op_fsm)
        if into != '=>':
            raise ValueError('Illegal operation: {}.'.format(line))

        reg3, i = self._parse_symbol(line, i, reg_fsm)
        reg3 = self._delete_prefix_0_for_reg(reg3)
        self.src_regs.add(reg3)

        op1 = ILOCOperand(sr=reg1)
        op2 = ILOCOperand(sr=reg2)
        op3 = ILOCOperand(sr=reg3)
        return ILOCOperation(opcode=opcode, op1=op1, op2=op2, op3=op3)

    def _parse_loadi(self, line, i):
        integer, i = self._parse_symbol(line, i, int_fsm)
        into, i = self._parse_symbol(line, i, op_fsm)
        if into != '=>':
            raise ValueError('Illegal operation: {}.'.format(line))

        reg, i = self._parse_symbol(line, i, reg_fsm)
        reg = self._delete_prefix_0_for_reg(reg)
        self.src_regs.add(reg)

        op1 = ILOCOperand(sr=integer)
        op3 = ILOCOperand(sr=reg)
        return ILOCOperation(opcode='loadI', op1=op1, op3=op3)

    def _parse_output(self, line, i):
        integer, i = self._parse_symbol(line, i, int_fsm)
        op1 = ILOCOperand(sr=integer)
        return ILOCOperation(opcode='output', op1=op1)

    @staticmethod
    def _delete_prefix_0_for_reg(reg):
        if reg != 'r0' and reg[:2] == 'r0':
            i = 1
            while reg[i] == '0':
                i += 1

            return 'r' + reg[i:]
        else:
            return reg
class ILOCOperation:
    def __init__(self, idx=-1, opcode=None, op1=None, op2=None, op3=None):
        self.idx = idx
        self.opcode = opcode
        self.op1 = op1
        self.op2 = op2
        self.op3 = op3
        self.comment = None

    def get_vr_str(self):
        arr = [self.opcode]
        if self.op1:
            val = self.op1.vr if self.op1.vr else self.op1.sr
            arr.append(val)
        if self.op2:
            arr[1] += ','
            arr.append(self.op2.vr)
        if self.op3:
            arr.append('=> ' + self.op3.vr)

        return ' '.join(arr)

    def get_pr_str(self):
        arr = [self.opcode]
        if self.op1:
            val = self.op1.pr if self.op1.pr else self.op1.sr
            arr.append(val)
        if self.op2:
            arr[1] += ','
            arr.append(self.op2.pr)
        if self.op3:
            arr.append('=> ' + self.op3.pr)

        if self.comment is None:
            self.comment = '\t// ' + self.get_vr_str()
        return ' '.join(arr) + self.comment

    def __str__(self):
        arr = [self.opcode, self.op1.sr]
        if self.op2:
            arr[1] += ','
            arr.append(self.op2.sr)
        if self.op3:
            arr.append('=> ' + self.op3.sr)

        return ' '.join(arr)


class ILOCOperand:
    def __init__(self, sr=None, vr=None, pr=None):
        self.sr = sr
        self.vr = vr
        self.pr = pr
        self.next_use = None
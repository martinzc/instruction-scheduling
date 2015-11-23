class StateMachine:
    def __init__(self, accept_states):
        self.handlers = {}
        self.accept_states = accept_states

    def add_state(self, state, handler):
        self.handlers[state] = handler

    def next_state(self, state, c):
        if state not in self.handlers:
            return -1

        return self.handlers[state](c)

    def is_accept_state(self, state):
        return state in self.accept_states


def int_fsm_s0_handler(c):
    if not '0' <= c <= '9':
        return -1

    return 1 if c == '0' else 2


def op_fsm_s0_handler(c):
    states = {'s': 1, 'l': 8, 'r': 13, 'm': 19, 'a': 22, 'n': 25, 'o': 28, '=': 34, ',': 36}
    if c not in states:
        return -1

    return states[c]


def op_fsm_s1_handler(c):
    if c != 't' and c != 'u':
        return -1

    return 2 if c == 't' else 6


def op_fsm_s8_handler(c):
    if c != 'o' and c != 's':
        return -1

    return 9 if c == 'o' else 14

int_fsm = StateMachine({1, 2})
int_fsm.add_state(0, int_fsm_s0_handler)
int_fsm.add_state(2, lambda c: 2 if '0' <= c <= '9' else -1)

reg_fsm = StateMachine({2})
reg_fsm.add_state(0, lambda c: 1 if c == 'r' else -1)
reg_fsm.add_state(1, lambda c: 2 if '0' <= c <= '9' else -1)
reg_fsm.add_state(2, lambda c: 2 if '0' <= c <= '9' else -1)

op_fsm = StateMachine({5, 7, 11, 12, 18, 24, 27, 33, 35, 36})
op_fsm.add_state(0, op_fsm_s0_handler)
op_fsm.add_state(1, op_fsm_s1_handler)
op_fsm.add_state(2, lambda c: 3 if c == 'o' else -1)
op_fsm.add_state(3, lambda c: 4 if c == 'r' else -1)
op_fsm.add_state(4, lambda c: 5 if c == 'e' else -1)
op_fsm.add_state(6, lambda c: 7 if c == 'b' else -1)
op_fsm.add_state(8, op_fsm_s8_handler)
op_fsm.add_state(9, lambda c: 10 if c == 'a' else -1)
op_fsm.add_state(10, lambda c: 11 if c == 'd' else -1)
op_fsm.add_state(11, lambda c: 12 if c == 'I' else -1)
op_fsm.add_state(13, lambda c: 14 if c == 's' else -1)
op_fsm.add_state(14, lambda c: 15 if c == 'h' else -1)
op_fsm.add_state(15, lambda c: 16 if c == 'i' else -1)
op_fsm.add_state(16, lambda c: 17 if c == 'f' else -1)
op_fsm.add_state(17, lambda c: 18 if c == 't' else -1)
op_fsm.add_state(19, lambda c: 20 if c == 'u' else -1)
op_fsm.add_state(20, lambda c: 21 if c == 'l' else -1)
op_fsm.add_state(21, lambda c: 18 if c == 't' else -1)
op_fsm.add_state(22, lambda c: 23 if c == 'd' else -1)
op_fsm.add_state(23, lambda c: 24 if c == 'd' else -1)
op_fsm.add_state(25, lambda c: 26 if c == 'o' else -1)
op_fsm.add_state(26, lambda c: 27 if c == 'p' else -1)
op_fsm.add_state(28, lambda c: 29 if c == 'u' else -1)
op_fsm.add_state(29, lambda c: 30 if c == 't' else -1)
op_fsm.add_state(30, lambda c: 31 if c == 'p' else -1)
op_fsm.add_state(31, lambda c: 32 if c == 'u' else -1)
op_fsm.add_state(32, lambda c: 33 if c == 't' else -1)
op_fsm.add_state(34, lambda c: 35 if c == '>' else -1)
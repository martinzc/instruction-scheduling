from os import path
from sys import argv, stderr

from scheduler import Scheduler
from ILOCScanner import ILOCScanner


HELP = '''
USAGE:
schedule -h
Produce a list of valid command-line arguments.

schedule <file name>
Produce an ILOC program that is equivalent to the input program,
albeit reordered to improve its execution time on the ILOC virtual
machine.
'''


def main():
    if len(argv) >= 2 and argv[1] == '-h':
        print(HELP)
    elif len(argv) >= 2:
        if not path.exists(argv[1]):
            raise IOError('Could not find the file {}.'.format(argv[1]))

        scanner = ILOCScanner()
        operations, src_regs = scanner.scan_file(argv[2])
        scheduler = Scheduler(operations, src_regs)
        scheduler.rename_regs()
        scheduler.build_dependence_graph()
        scheduler.perform()
    else:
        print('Wrong arguments.')


if __name__ == '__main__':
    try:
        main()
    except (IOError, ValueError), e:
        print >> stderr, e
        exit(1)
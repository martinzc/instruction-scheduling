from ILOCScanner import ILOCScanner
from scheduler import Scheduler

scanner = ILOCScanner()
operations, src_regs = scanner.scan_file('report/report08.i')
scheduler = Scheduler(operations, src_regs)
scheduler.rename_regs()
scheduler.build_dependence_graph()

with open('graph.dot', 'w') as f:
    f.write(scheduler.to_graph())

scheduler.perform()
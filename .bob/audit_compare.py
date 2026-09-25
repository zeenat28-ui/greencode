import sys
sys.path.insert(0, '.')
from app.parser import audit_file

before = audit_file('samples/heavy_pipeline.py')
after  = audit_file('samples/heavy_pipeline_refactored.py')

print('=== BEFORE ===')
print('Green Score :', before['green_score'])
print('Deductions  :', before['total_deductions'])
print('Violations  :', len(before['violations']))
for v in before['violations']:
    print('  [' + v['severity'] + '] L' + str(v['line_number']) + ' ' + v['violation_type'])

print()
print('=== AFTER (refactored) ===')
print('Green Score :', after['green_score'])
print('Deductions  :', after['total_deductions'])
print('Violations  :', len(after['violations']))
for v in after['violations']:
    print('  [' + v['severity'] + '] L' + str(v['line_number']) + ' ' + v['violation_type'])

print()
print('=== DELTA ===')
print('Score gain  :', round(after['green_score'] - before['green_score'], 2))
print('Deduction removed:', round(before['total_deductions'] - after['total_deductions'], 2))
print('Violations cleared:', len(before['violations']) - len(after['violations']))

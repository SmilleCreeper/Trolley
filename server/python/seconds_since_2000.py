import argparse, json, time
from datetime import datetime, timezone

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
p.add_argument('--progress', required=True)
args = p.parse_args()

def report(percent, message):
    with open(args.progress, 'w') as f:
        json.dump({'percent': percent, 'message': message}, f)

report(0, 'Connecting to temporal database...')
time.sleep(0.3)
report(25, 'Querying epoch boundaries...')
time.sleep(0.3)
report(50, 'Computing UTC delta...')
time.sleep(0.3)
report(75, 'Verifying leap seconds...')
time.sleep(0.3)

result = {'seconds': int((datetime.now(timezone.utc) - datetime(2000, 1, 1, tzinfo=timezone.utc)).total_seconds())}
report(100, 'Complete')
with open(args.output, 'w') as f:
    json.dump(result, f)

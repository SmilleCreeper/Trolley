import argparse, json
from datetime import datetime, timezone

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
p.add_argument('--progress', required=True)
args = p.parse_args()

result = {'iso': datetime.now(timezone.utc).isoformat()}
with open(args.output, 'w') as f:
    json.dump(result, f)

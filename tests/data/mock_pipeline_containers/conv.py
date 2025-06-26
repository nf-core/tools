import json

with open("containers.json") as fh:
    o = json.load(fh)

containers = {}
for p in o["processes"]:
    containers[p["name"]] = p["container"]

sorted_containers = dict(sorted(containers.items()))
with open("pipeline_containers.json", "w") as fh:
    json.dump(sorted_containers, fh, indent=4)

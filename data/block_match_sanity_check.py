import json

from transit_lab_simmetro.utils import project_root

file_name = project_root / "file.json"


def sanity_check(data):
    cn_blocks = [block for block in data if block["BRANCH"] == "CN"]

    # Sort the blocks based on the STARTSTN
    # cn_blocks.sort(key=lambda x: x["STARTSTN"])

    mismatched_blocks = []
    for i in range(1, len(cn_blocks)):
        if cn_blocks[i]["ENDSTN"] != cn_blocks[i - 1]["STARTSTN"]:
            mismatched_blocks.append((cn_blocks[i - 1]["BLOCK"], cn_blocks[i]["BLOCK"]))

    # Check for blocks communicating speed codes to blocks that are ahead of them
    seen_blocks = set()
    violations = []
    for block in cn_blocks:
        for communicated_block in block["SPEED_CODES_TO_COMMUNICATE"]:
            if communicated_block not in seen_blocks:
                violations.append((block["BLOCK"], communicated_block))
        seen_blocks.add(block["BLOCK"])

    return mismatched_blocks, violations


with open(file_name, "r") as f:
    data = json.load(f)
    mismatched_blocks, violations = sanity_check(data)

    for i, block in enumerate(data):
        if block["BLOCK"] == "WC-16":
            print(i)
            print(block)

print("Mismatched blocks:")
for block1, block2 in mismatched_blocks:
    print(f"Block {block1} ENDSTN doesn't match Block {block2} STARTSTN")

print("\nViolations:")
for block1, block2 in violations:
    print(
        f"Block {block1} is communicating speed codes to Block {block2} which is ahead in the order"
    )

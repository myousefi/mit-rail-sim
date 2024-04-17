import json

from mit_rail_sim.utils import project_root


# Function to create BLOCK_ALT based on the rules provided
def create_block_alt(block):
    # Separate digits and alphabets
    alphabets = "".join(filter(str.isalpha, block)).lower()
    digits = "".join(filter(str.isdigit, block))

    # Replace 'c' with 'dc' and add trailing 't' if alphabets are present
    # alphabets = alphabets.replace("c", "dc")
    if alphabets == "d":
        alphabets = "dd"

    # Ensure digits are always 3 or more, add 0s if needed
    digits = digits.zfill(3)

    # Join the modified alphabets and digits to form BLOCK_ALT
    block_alt = alphabets + digits + ("t" if alphabets else "")
    return block_alt


# import pandas as pd

# df = pd.read_csv(project_root / "temp_scripts" / "tracks.csv")
# df.to_json("./tracks.json", orient="records", indent=4)
# # Load the JSON file
# with open("./tracks.json", "r") as file:
#     data = json.load(file)


def approx_speed_code(data, index):
    sc = {}
    for i in range(1, min(index + 1, 11)):
        dist = sum([block["DISTANCE"] for block in data[index - i + 1 : index]])

        if dist < 500:
            speed = 0
        elif dist < 700:
            speed = 15
        elif dist < 1200:
            speed = 25
        elif dist < 2100:
            speed = 35
        else:
            speed = 100

        if speed < data[index - i]["SPEED"]:
            sc[data[index - i]["BLOCK"]] = speed
        # if dist < 800:
        #     sc[data[index - i]["BLOCK"]] = 0
        # elif dist < 2000:
        #     if data[index - i]["SPEED"] > 15:
        #         sc[data[index - i]["BLOCK"]] = 15
        # elif dist < 4000:
    return sc


with open(project_root / "alt_file_southbound_updated.json", "r") as file:
    data = json.load(file)

# Iterate over each entry in the JSON data
for index, entry in enumerate(data):
    # entry["SPEED_CODES_TO_COMMUNICATE"] = approx_speed_code(data, index)
    # entry["BLOCK_ALT"] = create_block_alt(entry["BLOCK"])
    if entry["BLOCK"] == "WD-1":
        print(entry)
        break
    entry["STARTSTN"], entry["ENDSTN"] = entry["ENDSTN"], entry["STARTSTN"]
    # swap start and end
# Save the modified JSON back to the file
with open(project_root / "alt_file_southbound_updated_.json", "w") as file:
    json.dump(data, file, indent=4)

print("File has been updated!")

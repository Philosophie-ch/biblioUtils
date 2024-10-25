from replace_map_240909 import REPLACEMENT_MAP


def replace_text(text: str, replacement_map: dict):
    for old, new in replacement_map.items():
        text = text.replace(old, new)
    return text

# File paths
input_file = '0-new-biblio-0-all-in-here-69.csv'
output_file = 'output.csv'

# Open the input file, read each line, apply the replacements, and write to the output file
with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
    for line in infile:
        # Strip newline characters from the line and replace the text
        replaced_line = replace_text(line, REPLACEMENT_MAP)
        outfile.write(replaced_line)

print(f"Replacements completed. Check '{output_file}' for the output.")

import requests
import json
import os
url = "https://hub.docker.com/v2/repositories/uiaegisv3/?page_size=100"
data = requests.get(url).json()

containerData = { "server": {}, "management": {}, "other": {}}
containerTags = { "server": {}, "management": {}, "other": {}}

DEFAULT_COLOR = "#9ca3af"
DEFAULT_LABEL = "UNK"


for container in data.get('results', []):
    desc = container.get('description')
    if not desc:
        continue
        
    description_chunks = desc.split()
    if len(description_chunks) < 2:
            continue

    color = description_chunks[3] if len(description_chunks) > 3 else DEFAULT_COLOR
    label = description_chunks[4] if len(description_chunks) > 4 else DEFAULT_LABEL

    if description_chunks[0] == "server":
        containerData["server"][description_chunks[1]+"-server"] = {"name": description_chunks[1].capitalize()+" Server", "label": label, "color": color}
    elif description_chunks[0] == "management":
        containerData["management"][description_chunks[1]] = {"name": description_chunks[1], "label": label, "color": color}
    else:
        containerData["other"][description_chunks[1]] = {"name": description_chunks[1], "label": label, "color": color}

    count = 5
    tags = []
    while count < len(description_chunks) and description_chunks[count] != "#":
        tags.append(description_chunks[2]+" "+description_chunks[count])
        count +=1

    if description_chunks[0] == "server":
        containerTags["server"][description_chunks[1]+"-server"] = tags
    elif description_chunks[0] == "management":
        containerTags["management"][description_chunks[1]] = tags
    else:
        containerTags["other"][description_chunks[1]] = tags

    if len(tags) == 0:
        tags.append(description_chunks[2]+" latest" )






def generate_aspects_file():
    all_types = []
    type_options = []
    type_colors = []
    type_labels = []
    type_display_names = []

    
    for items in containerData.values():
        for ctype, data in items.items():
            all_types.append(f"  | '{ctype}'")
            type_options.append(f"  {{ value: '{ctype}', label: '{data['name']}' }}")
            type_colors.append(f"  '{ctype}': '{data['color']}'")
            type_labels.append(f"  '{ctype}': '{data['label']}'")
            type_display_names.append(f"  '{ctype}': '{data['name']}'")

            
    ts_content = f"""
export type ContainerType =
{chr(10).join(all_types)};

export const typeOptions = [
{",".join(type_options)}
];

export const typeColors: Record<ContainerType, string> = {{
{",".join(type_colors)}
}};

export const typeLabels: Record<ContainerType, string> = {{
{",".join(type_labels)}
}};

export const typeDisplayNames: Record<string, string> = {{
{",".join(type_display_names)}
}};

export const menuHierarchy: Record<string, Partial<Record<ContainerType, string[]>>> = {json.dumps(containerTags, indent=2)};
"""

    script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create the absolute path for the output file
    output_path = os.path.join(script_dir, "ContainerAspects.tsx")
        
    with open(output_path, "w") as f:
        f.write(ts_content)

    print(f"Successfully wrote aspects to {output_path}")

generate_aspects_file()
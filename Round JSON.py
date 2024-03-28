import json

def round_json_values(input_filename, output_filename):
    # Load the data from the input JSON file
    with open(input_filename, 'r') as file:
        data = json.load(file)

    # Function to recursively round all numeric values in the data
    def round_values(item):
        if isinstance(item, dict):
            return {key: round_values(value) for key, value in item.items()}
        elif isinstance(item, list):
            return [round_values(element) for element in item]
        elif isinstance(item, (int, float)):
            return round(item)
        else:
            return item

    # Round all numeric values in the data
    rounded_data = round_values(data)

    # Write the rounded data to the output JSON file
    with open(output_filename, 'w') as file:
        json.dump(rounded_data, file, indent=4)

# Example usage
round_json_values('data/Ganz Strategy Score 174.63.json', 'data/Ganz Strategy Score 174.63 - rounded.json')

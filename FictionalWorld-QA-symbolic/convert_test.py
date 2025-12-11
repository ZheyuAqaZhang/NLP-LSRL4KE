'''
Step 1. read test.json
which looks like:
[
  {
    "id": "symbolic_0931",
    "question": "Based on the globally defined rules, what is the value of '( 8 * 3 ) * 2 / 4'?",
    "options": {
      "A": "11.0",
      "B": "-1.67",
      "C": "12.0",
      "D": "-2.67"
    },
    "answer": "D",
    "mapping": {
      "+": "*",
      "-": "+",
      "*": "/",
      "/": "-"
    }
  },
...

Step 2. convert it to non_replace_test.json (calculate the new answer based on the original formula), which looks like:
[
  {
    "id": "symbolic_0931",
    "question": "What is the value of '( 8 * 3 ) * 2 / 4'?",
    "options": {
      "A": "11.0",
      "B": "-1.67",
      "C": "12.0",
      "D": "-2.67"
    },
    "answer": "C"  # if the answer is not found, raise an error (rounded answer is acceptable)
  },
...

'''


import json
import operator
import re

# Safe evaluation with remapped operators
def evaluate_with_mapping(expr, mapping):
    # Replace operators based on mapping dictionary
    # IMPORTANT: ensure longer operators are replaced first (e.g., '//' before '/')
    # for orig, new in sorted(mapping.items(), key=lambda x: -len(x[0])):
    #     expr = expr.replace(orig, new)

    # Evaluate safely
    return eval(expr)


def normalize_number(x):
    """Round to 2 decimals for matching options."""
    return round(float(x), 2)


def convert_file(input_path="test.json", output_path="non_replace_test.json"):
    with open(input_path, "r") as f:
        data = json.load(f)

    new_data = []

    for item in data:
        expr = item["question"]
        # extract expression inside quotes: e.g. '( 8 * 3 ) * 2 / 4'
        match = re.search(r"'(.+?)'", expr)
        if not match:
            raise ValueError(f"Could not extract expression in: {expr}")

        raw_expr = match.group(1)
        mapped_expr = raw_expr

        # evaluate new formula using mapping
        result = evaluate_with_mapping(mapped_expr, item["mapping"])
        result_norm = normalize_number(result)

        # match result to options
        options = item["options"]
        matched_answer = None

        for key, val in options.items():
            if normalize_number(val) == result_norm:
                matched_answer = key
                break

        if matched_answer is None:
            raise ValueError(
                f"No matching option for expression {raw_expr}. "
                f"Computed={result_norm}, Options={options}"
            )

        # construct new item
        new_item = {
            "id": item["id"],
            "question": f"What is the value of '{raw_expr}'?",
            "options": options,
            "answer": matched_answer
        }
        new_data.append(new_item)

    # write output
    with open(output_path, "w") as f:
        json.dump(new_data, f, indent=2)

    print(f"✓ Successfully wrote: {output_path}")


if __name__ == "__main__":
    convert_file()

'''
step 1. load '../subset dataset/counterfact_result_evaluation.json' (three jsons)

the data structure is like this:

[
  {
    "state": "Seth is lucky.",
    "modify_state": "Seth is not lucky.",
    "counterfact": "All fast food restaurants worldwide only serve plain burgers now.",
    "assignment_id": "3KJYX6QCMAZPF8X79IF39OSNSSTJVE",
    "title": "Seth wins big",
    "dataset": "test",
    "original_story_lines": [
      "Seth is on vacation in Las Vegas.",
      "He decides to go to the casino.",
      "He tries his hand in playing some slots.",
      "He puts his money into the machine and plays.",
      "Seth wins the big prize from the slot machine."
    ],
    "modified_story_lines": [
      "Seth is on vacation in Las Vegas.",
      "He decides to go to the casino.",
      "He tries his hand in playing some slots.",
      "He puts his money into the machine and plays.",
      "Seth admires the big prize from the slot machine but doesn't win."
    ],
    "modified_line_indices": [
      5
    ],
    "line_modifications": [
      {
        "line_number": 5,
        "original_text": "Seth wins the big prize from the slot machine.",
        "modified_text": "Seth admires the big prize from the slot machine but doesn't win.",
        "change_description": "Line 5 changed"
      }
    ],
    "question": "Here are the story lines:\nSeth is on vacation in Las Vegas.\nHe decides to go to the casino.\nHe tries his hand in playing some slots.\nHe puts his money into the machine and plays.\n\nQuestion: Based on the globally defined rules, how does the story evolve?",
    "answer_choices": [
      {
        "text": "Seth is lucky.",
        "type": "standard_trap"
      },
      {
        "text": "Jane got a good grade.",
        "type": "misapplied_rule_distractor"
      },
      {
        "text": "Greg is not ambitious.",
        "type": "near_miss_distractor"
      },
      {
        "text": "Seth is not lucky.",
        "type": "correct"
      }
    ],
    "correct_choice_index": 3,
    "original_counterfact": "All slot machines worldwide are rigged to never pay out on any win attempts, ensuring players never receive any prize money.",
    "replacement_similarity_score": 0.6371681415929203,
    "counterfact_replaced": true,
    "original_counterfact_before_subset100": "All roulette tables worldwide now operate with rigged outcomes, ensuring players never win real money."
  },
...

Step 2. convert it to the new structure like:

[
  {
    "id": "symbolic_0931",   # assignment_id
    "question": "Based on the globally defined rules, what is the value of '( 8 * 3 ) * 2 / 4'?",  # question
    "options": {  # remember to shuffle the options
      "A": "11.0",
      "B": "-1.67",
      "C": "12.0",
      "D": "-2.67"
    },
    "answer": "D",  # the correct_choice_index after shuffle, map to A/B/C/D
    "counterfact": "TBD" # counterfact
  },
...

Step 3. create folders ./sub1 ./sub10 ./sub20

Note that in the file counterfactuals_list.txt:
(which looks like:

1. All fast food restaurants worldwide only serve plain burgers now.

2. All marriage ceremonies worldwide have been temporarily banned due to a global pandemic of mythical creatures that interfere with wedding rituals.

3. telecommunications systems suddenly went silent for 30 minutes.

4. instantaneously dissolved all marriages worldwide, effective immediately.

5. instantly turns all fishing gear into water skiing equipment worldwide.

6. instantaneously erased all romantic relationships worldwide, forcing everyone to reevaluate their connection statuses.

...
)

the txt file includes 100 counterfacts. so we will use sub1 for randomly select 1 counterfact, sub10 for 10 counterfacts, sub20 for 20 counterfacts.

Step 4. save train.json and test.json in each folder.
'''

import json
import os
import random
from typing import Dict, List, Any

# -------------------
# UPDATED CONFIG (your paths)
# -------------------
INPUT_TEST_JSON_PATH = "../subset dataset/counterfact_result_evaluation.json"
INPUT_TRAIN_JSON_PATH = "../subset dataset/counterfact_result_train.json"
COUNTERFACTS_TXT_PATH = "../subset dataset/counterfactuals_list.txt"

OUTPUT_DIRS = {
    1: "sub1",
    10: "sub10",
    20: "sub20",
}

RANDOM_SEED = 42  # reproducibility


# -------------------
# UTILITIES
# -------------------
def load_counterfacts_from_txt(path: str) -> List[str]:
    """
    Read counterfactuals_list.txt and return a list of plain counterfactual strings.
    Removes the numbered prefix "N. "
    """
    counterfacts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if ". " in line:
                try:
                    num_str, rest = line.split(". ", 1)
                    int(num_str)  # check numeric prefix
                    line = rest
                except ValueError:
                    pass

            counterfacts.append(line)
    return counterfacts


def convert_example(ex: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert example to:
    {
        "id": assignment_id,
        "question": question,
        "options": {A:...,B:...,C:...,D:...},
        "answer": correct_letter,
        "counterfact": counterfact
    }
    """
    assignment_id = ex["assignment_id"]
    question = ex["question"]
    answer_choices = ex["answer_choices"]
    correct_idx = ex["correct_choice_index"]
    counterfact = ex.get("counterfact", "TBD")

    option_entries = []
    for i, choice in enumerate(answer_choices):
        option_entries.append(
            {"text": choice["text"], "is_correct": (i == correct_idx)}
        )

    random.shuffle(option_entries)

    letters = ["A", "B", "C", "D"]
    options_dict = {}
    correct_letter = None

    for i, opt in enumerate(option_entries):
        letter = letters[i]
        options_dict[letter] = opt["text"]
        if opt["is_correct"]:
            correct_letter = letter

    if correct_letter is None:
        raise RuntimeError(f"No correct option found after shuffle for {assignment_id}")

    return {
        "id": assignment_id,
        "question": question,
        "options": options_dict,
        "answer": correct_letter,
        "counterfact": counterfact,
    }


def ensure_dirs():
    for _, dirname in OUTPUT_DIRS.items():
        os.makedirs(dirname, exist_ok=True)


# -------------------
# MAIN PIPELINE
# -------------------
def main():
    random.seed(RANDOM_SEED)

    # Step 1 — Load train & test explicitly
    with open(INPUT_TEST_JSON_PATH, "r", encoding="utf-8") as f:
        test_raw = json.load(f)

    with open(INPUT_TRAIN_JSON_PATH, "r", encoding="utf-8") as f:
        train_raw = json.load(f)

    # All counterfacts grouped from JSON data
    counterfact_to_examples = {}

    for split_name, examples in [("train", train_raw), ("test", test_raw)]:
        for ex in examples:
            cf = ex.get("counterfact", "TBD")
            counterfact_to_examples.setdefault(cf, {}).setdefault(split_name, []).append(ex)

    # Step 2 — Load the 100 CFs from txt
    all_cf_txt = load_counterfacts_from_txt(COUNTERFACTS_TXT_PATH)

    # Step 3 — Make folders
    ensure_dirs()

    # Step 4 — For each subset size, sample CFs, collect train/test, save JSON
    for k, dirname in OUTPUT_DIRS.items():
        chosen_cfs = random.sample(all_cf_txt, k)

        subset_out = {"train": [], "test": []}

        for cf in chosen_cfs:
            if cf not in counterfact_to_examples:
                continue

            for split_name in ["train", "test"]:
                raw_list = counterfact_to_examples[cf].get(split_name, [])
                for ex in raw_list:
                    subset_out[split_name].append(convert_example(ex))

        for split_name in ["train", "test"]:
            out_path = os.path.join(dirname, f"{split_name}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(subset_out[split_name], f, indent=2, ensure_ascii=False)

        print(f"[{dirname}] Selected {k} counterfacts → "
              f"train={len(subset_out['train'])}, test={len(subset_out['test'])}")


if __name__ == "__main__":
    main()


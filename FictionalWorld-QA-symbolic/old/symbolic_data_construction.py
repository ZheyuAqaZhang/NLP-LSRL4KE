import random
import json
import math

# ==============================================================================
# 1. GLOBAL UNIFIED COUNTERFACTUAL RULES
# This rule set applies to all questions in the dataset.
# '+' -> Multiplication (*)
# '-' -> Addition (+)
# '*' -> Division (/)
# '/' -> Subtraction (-)
# ==============================================================================
GLOBAL_TWISTED_RULES = {
    '+': '*',
    '-': '+',
    '*': '/',
    '/': '-'
}

def translate_expression(expression, rules):
    """Translate operators in the expression based on the rules."""
    tokens = expression.split(' ')
    # Replace each operator
    new_tokens = [rules.get(token, token) for token in tokens]
    return ' '.join(new_tokens)

def evaluate_counterfactual(expression_str):
    """
    Safely calculates the 'correct' answer under the twisted rules.
    Returns None if an error (like ZeroDivision) occurs.
    """
    try:
        twisted_expression = translate_expression(expression_str, GLOBAL_TWISTED_RULES)
        result = eval(twisted_expression)
        return round(result, 2)
    except ZeroDivisionError:
        return None
    except Exception as e:
        # print(f"Error in counterfactual eval: {twisted_expression} | {e}")
        return None

def evaluate_standard(expression_str):
    """
    Safely calculates the 'real-world trap' answer.
    Returns None if an error (like ZeroDivision) occurs.
    """
    try:
        result = eval(expression_str)
        return round(result, 2)
    except ZeroDivisionError:
        return None
    except Exception as e:
        # print(f"Error in standard eval: {expression_str} | {e}")
        return None

def generate_expression(complexity: int, num_range: tuple):
    """
    Generates a robust mathematical expression, avoiding division by zero.
    
    complexity: Number of operands (e.g., 2 for 'a + b')
    num_range: (min, max) tuple for operands
    """
    operators = list(GLOBAL_TWISTED_RULES.keys())
    tokens = []
    (min_val, max_val) = num_range

    # Add the first number
    tokens.append(str(random.randint(min_val, max_val)))

    for _ in range(complexity - 1):
        # 1. Choose an operator
        op = random.choice(operators)
        tokens.append(op)
        
        # 2. Generate a safe operand
        # If op is '*' (becomes /) or '/' (standard /), the next number cannot be 0.
        current_min = min_val
        if op in ('*', '/'):
            if current_min == 0:
                current_min = 1
            elif max_val == 0:
                max_val = -1
        
        if current_min > max_val:
            current_min = max_val
            if current_min == 0: 
                current_min = 1
                max_val = 1
        
        num = random.randint(current_min, max_val)
        
        if num == 0 and op in ('*', '/'):
            num = 1
            
        tokens.append(str(num))

    expression_str = ' '.join(tokens)

    # 3. Add parentheses for diversity in complex expressions
    if complexity >= 4 and random.random() < 0.25:
        start_token_idx = random.randrange(0, (complexity - 2) * 2, 2)
        tokens.insert(start_token_idx, '(')
        tokens.insert(start_token_idx + 4, ')')
        expression_str = ' '.join(tokens)

    return expression_str

# ==============================================================================
# MODIFIED FUNCTION: generate_options
# ==============================================================================
def generate_options(expression_str, correct_answer, trap_answer, num_options=4):
    """
    Generates a plausible list of multiple-choice options, including the correct
    answer, the trap, and smarter distractors.
    """
    # Set of potential options, starting with the two most important
    options = {correct_answer, trap_answer}
    
    # --- Distractor Pool Generation ---
    distractor_pool = set()
    
    # Strategy 1: Misapplied Rule (The best one)
    tokens = expression_str.split(' ')
    op_indices = [i for i, token in enumerate(tokens) if token in GLOBAL_TWISTED_RULES]
    
    if op_indices:
        # Try to create 2 "misapplied rule" distractors
        for _ in range(2):
            try:
                idx_to_change = random.choice(op_indices)
                original_op = tokens[idx_to_change]
                
                # Get a list of *other* rules
                other_ops = [op for op in GLOBAL_TWISTED_RULES.keys() if op != original_op]
                if not other_ops: continue
                
                new_op = random.choice(other_ops)
                
                # Create the new "mistake" expression
                new_tokens = list(tokens)
                new_tokens[idx_to_change] = new_op
                new_expression = ' '.join(new_tokens)
                
                # Evaluate this new "mistake" expression using counterfactual rules
                mistake_answer = evaluate_counterfactual(new_expression)
                
                if mistake_answer is not None:
                    distractor_pool.add(mistake_answer)
            except Exception:
                continue # Fail silently if token/parsing fails

    # Strategy 2: Hybrid Relative/Absolute Offset
    # Generate distractors near both the correct answer and the trap answer
    for base_val in [correct_answer, trap_answer]: 
        # Relative part: 10-50% of the value
        relative_offset = abs(base_val) * random.uniform(0.1, 0.5)
        # Absolute part: 0.5-2.0
        absolute_offset = random.uniform(0.5, 2.0)
        
        # Combine them and apply a random sign
        total_offset = (relative_offset + absolute_offset) * random.choice([-1, 1])
        
        decoy = round(base_val + total_offset, 2)
        distractor_pool.add(decoy)
    
    # Strategy 3: Small Integer Offset (Off-by-one errors)
    distractor_pool.add(round(correct_answer + random.choice([-1, 1, 2]), 2))
    distractor_pool.add(round(trap_answer + random.choice([-1, 1]), 2))
    
    # --- Fill options from the pool ---
    # Convert pool to a list and shuffle
    # Only include distractors that aren't already in our main options set
    shuffled_distractors = [d for d in distractor_pool if d not in options and d is not None]
    random.shuffle(shuffled_distractors)
    
    # Add distractors to options until we have enough
    for decoy in shuffled_distractors:
        if len(options) >= num_options:
            break
        options.add(decoy)
            
    # Failsafe: If we *still* don't have enough (e.g., all decoys were duplicates),
    # fall back to a slightly-less-random offset.
    while len(options) < num_options:
        base_val = random.choice([correct_answer, trap_answer])
        # Use a smaller, more controlled offset than the original code
        offset = (abs(base_val) * random.uniform(0.1, 0.3) + random.uniform(0.5, 3.0)) * random.choice([-1, 1])
        decoy = round(base_val + offset, 2)
        
        if decoy not in options:
            options.add(decoy)

    option_list = list(options)
    random.shuffle(option_list)
    # Ensure we only return the number of options requested
    return option_list[:num_options]
# ==============================================================================
# END OF MODIFIED FUNCTION
# ==============================================================================


def generate_unified_dataset(total_samples=1000):
    """
    Generates the complete dataset based on the curriculum.
    """
    dataset = []
    global_id = 1
    
    # Define the curriculum structure
    curriculum_plan = {
        2: int(total_samples * 0.20),  # 200 samples
        3: int(total_samples * 0.30),  # 300 samples
        4: int(total_samples * 0.30),  # 300 samples
        5: int(total_samples * 0.20),  # 200 samples
    }
    
    # Define the number magnitude stages
    magnitude_stages = [(1, 10), (10, 25), (25, 50), (50, 100)]
    
    print("Starting dataset generation...")

    for complexity, num_samples in curriculum_plan.items():
        print(f"--- Generating {num_samples} samples for Complexity Level {complexity} ---")
        
        for i in range(num_samples):
            stage_index = min(i // (num_samples // len(magnitude_stages)), len(magnitude_stages) - 1)
            num_range = magnitude_stages[stage_index]

            retries = 0
            while retries < 10: 
                expression_str = generate_expression(complexity, num_range)
                
                correct_answer = evaluate_counterfactual(expression_str)
                trap_answer = evaluate_standard(expression_str)
                
                if correct_answer is None or trap_answer is None:
                    retries += 1
                    continue
                    
                if abs(correct_answer - trap_answer) < 1e-9:
                    retries += 1
                    continue
                break
            else:
                print(f"Warning: Skipping sample for complexity {complexity} after 10 retries.")
                continue

            # ============================================================
            # MODIFIED CALL: Pass expression_str to generate_options
            # ============================================================
            options_list = generate_options(expression_str, correct_answer, trap_answer)
            # ============================================================

            options_dict = {chr(65 + j): str(val) for j, val in enumerate(options_list)}
            
            correct_label = ""
            for label, val in options_dict.items():
                if abs(float(val) - correct_answer) < 1e-9:
                    correct_label = label
                    break
            
            question_data = {
                "id": f"symbolic_{global_id:04d}",
                "complexity_level": complexity,
                "question": f"Based on the globally defined rules, what is the value of '{expression_str}'?",
                "expression": expression_str,
                "options": options_dict,
                "correct_answer": correct_label,
                "debug_info": {
                    "counterfactual_answer": correct_answer,
                    "standard_trap_answer": trap_answer,
                    "counterfactual_expression": translate_expression(expression_str, GLOBAL_TWISTED_RULES)
                }
            }
            dataset.append(question_data)
            global_id += 1

    final_dataset = {
        "metadata": {
            "dataset_name": "Fictional World QA",
            "description": "Symbolic based dataset",
            "total_samples": len(dataset),
            "global_rules_applied": {original: new for original, new in GLOBAL_TWISTED_RULES.items()}
        },
        "questions": dataset
    }
    
    print(f"\nGeneration complete. Total samples created: {len(dataset)}")
    return final_dataset

# --- Main execution ---
if __name__ == "__main__":
    symbolic_dataset = generate_unified_dataset(total_samples=1000)
    
    output_filename = "symbolic_dataset.json"

    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(symbolic_dataset, f, indent=2, ensure_ascii=False)
        
        print(f"\nSuccessfully saved dataset to '{output_filename}'")
        
        # Print a few samples to verify
        print("\n--- Sample Data Preview (First 3) ---")
        print(json.dumps(symbolic_dataset["questions"][:3], indent=2))
        
        print("\n--- Sample Data Preview (Last 3) ---")
        print(json.dumps(symbolic_dataset["questions"][-3:], indent=2))
        
    except Exception as e:
        print(f"Error saving file: {e}")
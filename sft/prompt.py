sft_prompt_template = """### Instruction
You are a logical reasoning assistant. Solve the multiple-choice question based strictly on the Global Replacement Rules.

### Global Replacement Rules
{rules}

### Problem
Question: {question}

### Options
{options_str}

### Output Format
Select the correct option. Give your final answer directly in the <answer> block with one of the options: A, B, C, D. You should provide your detailed reasoning step by step in the <think> block.
Format example: 
<think> Your detailed reasoning step by step. </think>
<answer>your final answer</answer>

### Response
"""

sft_prompt_withough_rules_template = """### Instruction
You are a logical reasoning assistant. Solve the multiple-choice question based strictly on the Global Replacement Rules.

### Problem
Question: {question}

### Options
{options_str}

### Output Format
Select the correct option. Give your final answer directly in the <answer> block. Do not provide reasoning or explanations.
Format example: <answer>A</answer>

### Response
"""

original_prompt_withough_rules_template = """### Instruction
You are a logical reasoning assistant. Solve the multiple-choice question.

### Problem
Question: {question}

### Options
{options_str}

### Output Format
Select the correct option. Give your final answer directly in the <answer> block. Do not provide reasoning or explanations.
Format example: <answer>A</answer>

### Response
"""

def make_sft_prompt(problem, options, mapping):
    return sft_prompt_template.format(rules=mapping, question=problem, options_str=options)

def make_sft_prompt_without_rules(problem, options):
    return sft_prompt_withough_rules_template.format(question=problem, options_str=options)

def make_original_prompt_without_rules(problem, options):
    return original_prompt_withough_rules_template.format(question=problem, options_str=options)
# FictionalWorld-QA: Symbolic Based Dataset

A counterfactual mathematics dataset designed to evaluate AI models' ability to learn, adapt to, and apply novel symbolic rules that contradict their pre-trained knowledge.

## Overview

This dataset contains 1,000 multiple-choice mathematical questions where standard arithmetic operators follow **globally redefined rules**. The purpose is to test whether language models can:

1. **Learn new symbolic systems** that contradict their training
2. **Override deeply ingrained knowledge** (standard mathematics)
3. **Consistently apply counterfactual rules** across varying complexity levels
4. **Resist the "real-world trap"** of reverting to standard arithmetic

## Counterfactual Rules

In this fictional world, mathematical operators are redefined as follows:

| Standard Operator | Fictional Meaning | Example |
|-------------------|-------------------|---------|
| `+` | Multiplication (`*`) | `5 + 3` = `5 * 3` = **15** |
| `-` | Addition (`+`) | `5 - 3` = `5 + 3` = **8** |
| `*` | Division (`/`) | `6 * 3` = `6 / 3` = **2** |
| `/` | Subtraction (`-`) | `6 / 3` = `6 - 3` = **3** |

**Important**: These rules are applied **globally and consistently** across all 1,000 questions in the dataset.

## Dataset Structure

### Metadata

```json
{
  "metadata": {
    "dataset_name": "Fictional World QA",
    "description": "Symbolic based dataset",
    "total_samples": 1000,
    "global_rules_applied": {
      "+": "*",
      "-": "+",
      "*": "/",
      "/": "-"
    }
  }
}
```

### Question Format

Each question contains:

```json
{
  "id": "symbolic_0001",
  "complexity_level": 2,
  "question": "Based on the globally defined rules, what is the value of '1 / 2'?",
  "expression": "1 / 2",
  "options": {
    "A": "1.91",
    "B": "-1.76",
    "C": "0.5",
    "D": "-1"
  },
  "correct_answer": "D",
  "debug_info": {
    "counterfactual_answer": -1,
    "standard_trap_answer": 0.5,
    "counterfactual_expression": "1 - 2"
  }
}
```

### Fields Explanation

- **id**: Unique identifier (`symbolic_XXXX`)
- **complexity_level**: Number of operands in the expression (2-5)
- **question**: The question text
- **expression**: The mathematical expression to evaluate
- **options**: Four multiple-choice options (A, B, C, D)
- **correct_answer**: The correct option label under counterfactual rules
- **debug_info**: 
  - `counterfactual_answer`: Correct answer under fictional rules
  - `standard_trap_answer`: Answer under standard mathematics (the trap)
  - `counterfactual_expression`: The expression after rule translation

## Curriculum Design

The dataset follows a progressive difficulty structure:

| Complexity Level | # of Operands | Samples | Percentage | Number Range |
|------------------|---------------|---------|------------|--------------|
| 2 | 2 | 200 | 20% | 1-100 (progressive) |
| 3 | 3 | 300 | 30% | 1-100 (progressive) |
| 4 | 4 | 300 | 30% | 1-100 (progressive) |
| 5 | 5 | 200 | 20% | 1-100 (progressive) |

### Magnitude Stages

Within each complexity level, number magnitudes increase progressively:
1. Stage 1: Numbers from 1-10
2. Stage 2: Numbers from 10-25
3. Stage 3: Numbers from 25-50
4. Stage 4: Numbers from 50-100

## Distractor Design

The multiple-choice options include sophisticated distractors:

1. **Trap Answer**: The result using standard mathematical rules (tests if model reverts to pre-trained knowledge)
2. **Misapplied Rule**: Results from partially or incorrectly applying the counterfactual rules
3. **Near-Miss Values**: Answers close to the correct value (off-by-one errors)
4. **Hybrid Offsets**: Plausible values generated through relative and absolute offsets

This design ensures that random guessing yields ~25% accuracy, while systematic errors reveal specific failure modes.

## Example Questions

### Easy (Complexity 2)
**Question**: Based on the globally defined rules, what is the value of `10 - 7`?

- **Correct Answer**: 17 (because `-` means `+`, so `10 + 7 = 17`)
- **Trap Answer**: 3 (standard mathematics)

### Medium (Complexity 3)
**Question**: Based on the globally defined rules, what is the value of `5 + 3 - 2`?

- **Correct Answer**: 17 (because `5 * 3 + 2 = 15 + 2 = 17`)
- **Trap Answer**: 6 (standard mathematics)

### Hard (Complexity 5)
**Question**: Based on the globally defined rules, what is the value of `8 / 4 + 2 * 3 - 1`?

- **Correct Answer**: 5.67 (because `8 - 4 * 2 / 3 + 1 = 4 * 2 / 3 + 1 = 8 / 3 + 1 = 2.67 + 1 = 3.67`)
- **Trap Answer**: 11 (standard mathematics)
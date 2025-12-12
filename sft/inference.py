"""
vLLM Inference Script for Qwen3-4B (Non-Thinking Mode)
Usage: 
    CUDA_VISIBLE_DEVICES=0 python inference.py [--model_path PATH] [--test_data PATH]
    or: python inference.py --gpu 0 [--model_path PATH] [--test_data PATH]
"""

import os
import sys
import json
import re
import argparse
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
from prompt import make_sft_prompt, make_sft_prompt_without_rules, make_original_prompt_without_rules


def parse_args():
    parser = argparse.ArgumentParser(description='vLLM Inference for Qwen3-4B')
    parser.add_argument('--model_path', type=str, default='Qwen/Qwen3-8B',
                        help='Path to the model (base or fine-tuned checkpoint)')
    parser.add_argument('--test_data', type=str,
                        default='/work/nvme/bdhh/jiang5/NLP-LSRL4KE/FictionalWorld-QA-symbolic/test.json',
                        help='Path to test data')
    parser.add_argument('--output', type=str, default='./inference_results_replace_test_cotckpt.json',
                        help='Path to save inference results')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size for inference')
    parser.add_argument('--max_tokens', type=int, default=2048,
                        help='Maximum tokens to generate')
    parser.add_argument('--temperature', type=float, default=0.0,
                        help='Sampling temperature (0 for greedy)')
    parser.add_argument('--gpu_memory_utilization', type=float, default=0.8,
                        help='GPU memory utilization for vLLM')
    parser.add_argument('--save_wrong', action='store_true',
                        help='Save wrong predictions to a separate file')
    parser.add_argument('--gpu', type=str, default=None,
                        help='GPU device ID (e.g., 0, 1, or 0,1 for multi-GPU)')
    parser.add_argument('--num_passes', type=int, default=1,
                        help='Number of passes for pass@k evaluation (default: 1)')
    return parser.parse_args()


def format_mapping(mapping: dict) -> str:
    """Format the mapping rules as a readable string."""
    lines = []
    for orig, replaced in mapping.items():
        lines.append(f"  {orig} -> {replaced}")
    return "\n".join(lines)


def format_options(options: dict) -> str:
    """Format the options as a readable string."""
    return "\n".join([f"{k}. {v}" for k, v in options.items()])


def build_prompt(item: dict, tokenizer) -> str:
    """Build the inference prompt for a single item."""
    # rules_str = format_mapping(item['mapping'])
    options_str = format_options(item['options'])
    
    # user_content = make_sft_prompt(item['question'], options_str, rules_str)

    user_content_without_rules = make_sft_prompt_without_rules(item['question'], options_str)
    # user_content_original_without_rules = make_original_prompt_without_rules(item['question'], options_str)
    # Build messages for chat template
    messages = [
        {"role": "user", "content": user_content_without_rules}
    ]
    
    # Apply chat template with generation prompt
    # For Qwen3, use enable_thinking=False for non-thinking mode
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True  # Qwen3 non-thinking mode
    )
    
    return prompt


def extract_answer(response: str) -> Optional[str]:
    """Extract the answer from model response."""
    # Try to find <answer>X</answer> pattern
    match = re.search(r"<answer>\s*([A-Da-d])\s*</answer>", response, re.DOTALL)
    if match:
        return match.group(1).upper()
    
    # Fallback: find any single letter A-D
    match = re.search(r"\b([A-Da-d])\b", response)
    if match:
        return match.group(1).upper()
    
    return None


def calculate_pass_at_k(results: List[Dict], k: int) -> float:
    """Calculate pass@k metric: percentage of samples with at least one correct prediction in k passes."""
    if k == 1:
        # For k=1, just return standard accuracy
        correct = sum(1 for item in results if item.get('prediction') == item.get('gold_answer'))
        return correct / len(results) if results else 0
    
    # For k>1, check if any of the k predictions is correct
    pass_at_k_correct = 0
    for item in results:
        predictions = item.get('predictions', [item.get('prediction')])
        gold = item.get('gold_answer')
        # Check if at least one prediction matches the gold answer
        if any(pred == gold for pred in predictions):
            pass_at_k_correct += 1
    
    return pass_at_k_correct / len(results) if results else 0


def evaluate_results(results: List[Dict], num_passes: int = 1) -> Dict:
    """Calculate evaluation metrics."""
    correct = 0
    total = len(results)
    wrong_items = []
    
    for item in results:
        pred = item.get('prediction')
        gold = item.get('gold_answer')
        
        if pred == gold:
            correct += 1
        else:
            wrong_items.append(item)
    
    accuracy = correct / total if total > 0 else 0
    
    # Calculate pass@k metric
    pass_at_k = calculate_pass_at_k(results, num_passes)
    
    return {
        'total': total,
        'correct': correct,
        'wrong': total - correct,
        'accuracy': accuracy,
        'pass_at_k': pass_at_k,
        'num_passes': num_passes,
        'wrong_items': wrong_items
    }


def main():
    args = parse_args()
    
    # Set GPU device if specified
    if args.gpu is not None:
        os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
        print(f"Using GPU: {args.gpu}")
    
    print("=" * 60)
    print("vLLM Inference Configuration")
    print("=" * 60)
    print(f"Model: {args.model_path}")
    print(f"Test Data: {args.test_data}")
    print(f"Output: {args.output}")
    print(f"Number of Passes (k): {args.num_passes}")
    print(f"Max Tokens: {args.max_tokens}")
    print(f"Temperature: {args.temperature}")
    print(f"GPU Memory Utilization: {args.gpu_memory_utilization}")
    print("=" * 60)
    
    # Load tokenizer
    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    
    # Load vLLM model
    print("Loading vLLM model...")
    llm = LLM(
        model=args.model_path,
        trust_remote_code=True,
        gpu_memory_utilization=args.gpu_memory_utilization,
        enable_chunked_prefill=True,
        enforce_eager=True
    )
    
    # Set sampling parameters
    # For multi-pass inference (n>1), temperature must be > 0
    temperature = args.temperature
    if args.num_passes > 1 and temperature == 0.0:
        temperature = 0.7  # Default temperature for multi-pass sampling
        print(f"⚠️  Warning: num_passes={args.num_passes} requires temperature>0. Setting temperature to {temperature}")
    
    sampling_params = SamplingParams(
        n=args.num_passes,
        temperature=temperature,
        max_tokens=args.max_tokens,
        stop=["<|im_end|>", "<|endoftext|>"]
    )
    
    # Load test data
    print("\nLoading test data...")
    with open(args.test_data, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    print(f"Loaded {len(test_data)} test samples")
    
    # Build prompts
    print("\nBuilding prompts...")
    prompts = [build_prompt(item, tokenizer) for item in test_data]
    
    # Run inference
    print("\nRunning inference...")
    outputs = llm.generate(prompts, sampling_params, use_tqdm=True)
    
    # Process results
    print("\nProcessing results...")
    results = []
    for item, output in zip(test_data, outputs):
        # Extract all predictions from all passes
        predictions = []
        generated_texts = []
        for output_item in output.outputs:
            generated_text = output_item.text
            prediction = extract_answer(generated_text)
            predictions.append(prediction)
            generated_texts.append(generated_text)
        
        # Check if at least one prediction is correct (for pass@k)
        gold_answer = item['answer']
        pass_at_k_correct = any(pred == gold_answer for pred in predictions)
        
        results.append({
            'id': item.get('id', ''),
            'question': item['question'],
            'options': item['options'],
            'gold_answer': gold_answer,
            'prediction': predictions[0],  # First pass for backward compatibility
            'predictions': predictions,  # All k passes
            'generated_text': generated_texts[0],  # First pass for backward compatibility
            'generated_texts': generated_texts,  # All k passes
            'correct': predictions[0] == gold_answer,  # First pass correctness
            'pass_at_k_correct': pass_at_k_correct  # At least one correct in k passes
        })
    
    # Evaluate
    eval_metrics = evaluate_results(results, args.num_passes)
    
    print("\n" + "=" * 60)
    print("Evaluation Results")
    print("=" * 60)
    print(f"Total Samples: {eval_metrics['total']}")
    print(f"Number of Passes (k): {eval_metrics['num_passes']}")
    print(f"Correct (1st pass): {eval_metrics['correct']}")
    print(f"Wrong (1st pass): {eval_metrics['wrong']}")
    print(f"Accuracy (1st pass): {eval_metrics['accuracy']:.4f} ({eval_metrics['accuracy']*100:.2f}%)")
    if eval_metrics['num_passes'] > 1:
        print(f"Pass@{eval_metrics['num_passes']}: {eval_metrics['pass_at_k']:.4f} ({eval_metrics['pass_at_k']*100:.2f}%)")
    print("=" * 60)
    
    # Save results
    output_data = {
        'model_path': args.model_path,
        'test_data': args.test_data,
        'num_passes': args.num_passes,
        'metrics': {
            'total': eval_metrics['total'],
            'num_passes': eval_metrics['num_passes'],
            'correct': eval_metrics['correct'],
            'wrong': eval_metrics['wrong'],
            'accuracy': eval_metrics['accuracy'],
            'pass_at_k': eval_metrics['pass_at_k']
        },
        'results': results
    }
    
    print(f"\nSaving results to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # Save wrong predictions if requested
    if args.save_wrong and eval_metrics['wrong_items']:
        wrong_file = args.output.replace('.json', '_wrong.json')
        print(f"Saving wrong predictions to {wrong_file}...")
        with open(wrong_file, 'w', encoding='utf-8') as f:
            json.dump(eval_metrics['wrong_items'], f, ensure_ascii=False, indent=2)
    
    # Print some examples of wrong predictions
    if eval_metrics['wrong_items']:
        print("\n--- Sample Wrong Predictions ---")
        for i, item in enumerate(eval_metrics['wrong_items'][:3]):
            print(f"\nExample {i+1}:")
            print(f"  Question: {item['question'][:80]}...")
            print(f"  Gold: {item['gold_answer']}")
            print(f"  Predicted: {item['prediction']}")
            print(f"  Generated: {item['generated_text'][:100]}...")
    
    print("\nInference complete!")
    return eval_metrics


if __name__ == '__main__':
    main()


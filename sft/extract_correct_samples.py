#!/usr/bin/env python3
"""
Extract one correct sample from each question to prepare training data.
从每道题中提取一个正确的样本作为训练数据。
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any


def extract_correct_samples(input_file: str, output_file: str, format_type: str = "sft"):
    """
    Extract one correct sample from each question.
    
    Args:
        input_file: Path to inference results JSON file
        output_file: Path to output training data file
        format_type: Output format type ("sft" or "raw")
    """
    # Read inference results
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    
    # Extract correct samples
    training_samples = []
    stats = {
        'total_questions': len(results),
        'questions_with_correct_answer': 0,
        'questions_without_correct_answer': 0,
        'skipped_questions': []
    }
    
    for result in results:
        question_id = result['id']
        question = result['question']
        options = result['options']
        gold_answer = result['gold_answer']
        predictions = result['predictions']
        generated_texts = result['generated_texts']
        
        # Find the first correct prediction
        correct_idx = None
        for idx, pred in enumerate(predictions):
            if pred == gold_answer:
                correct_idx = idx
                break
        
        if correct_idx is not None:
            # Found a correct sample
            stats['questions_with_correct_answer'] += 1
            
            # Format the sample based on format_type
            if format_type == "sft":
                # Standard SFT format with instruction and response
                # Construct the prompt with question and options
                options_text = "\n".join([f"{k}: {v}" for k, v in options.items()])
                prompt = f"{question}\n\nOptions:\n{options_text}"
                
                sample = {
                    "id": question_id,
                    "instruction": prompt,
                    "response": generated_texts[correct_idx],
                    "gold_answer": gold_answer,
                    "prediction": predictions[correct_idx]
                }
            else:
                # Raw format - keep original structure
                sample = {
                    "id": question_id,
                    "question": question,
                    "options": options,
                    "gold_answer": gold_answer,
                    "correct_response": generated_texts[correct_idx],
                    "correct_prediction": predictions[correct_idx]
                }
            
            training_samples.append(sample)
        else:
            # No correct prediction found
            stats['questions_without_correct_answer'] += 1
            stats['skipped_questions'].append(question_id)
    
    # Save training samples
    output_data = {
        "metadata": {
            "source_file": input_file,
            "format_type": format_type,
            "statistics": stats
        },
        "samples": training_samples
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # Print statistics
    print(f"✓ 处理完成!")
    print(f"\n统计信息:")
    print(f"  - 总题目数: {stats['total_questions']}")
    print(f"  - 有正确答案的题目: {stats['questions_with_correct_answer']}")
    print(f"  - 无正确答案的题目: {stats['questions_without_correct_answer']}")
    print(f"  - 提取的训练样本数: {len(training_samples)}")
    print(f"\n输出文件: {output_file}")
    
    if stats['skipped_questions']:
        print(f"\n跳过的题目 (共 {len(stats['skipped_questions'])} 个):")
        for qid in stats['skipped_questions'][:10]:  # Show first 10
            print(f"  - {qid}")
        if len(stats['skipped_questions']) > 10:
            print(f"  ... 还有 {len(stats['skipped_questions']) - 10} 个")


def main():
    parser = argparse.ArgumentParser(
        description='从推理结果中提取每道题的正确样本作为训练数据',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='输入的推理结果JSON文件路径'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        required=True,
        help='输出的训练数据JSON文件路径'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['sft', 'raw'],
        default='sft',
        help='输出格式类型: sft (指令微调格式) 或 raw (原始格式)'
    )
    
    args = parser.parse_args()
    
    # Check input file exists
    if not Path(args.input).exists():
        print(f"错误: 输入文件不存在: {args.input}")
        return
    
    # Extract correct samples
    extract_correct_samples(args.input, args.output, args.format)


if __name__ == '__main__':
    main()



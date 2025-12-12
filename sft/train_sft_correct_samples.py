"""
SFT Training Script using extracted correct samples (without rules template)
使用提取的正确样本进行SFT训练（不包含规则模板）

Usage: python train_sft_correct_samples.py \
    --train_data train_data_correct_samples.json \
    --model_path Qwen/Qwen3-8B \
    --output_dir ./sft_checkpoints_no_rules
"""

import os
import sys
import json
import argparse

import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from trl import SFTTrainer

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt import sft_prompt_withough_rules_template


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='SFT Training with extracted correct samples (no rules template)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--model_path', type=str, 
        default='Qwen/Qwen3-8B',
        help='Path to the base model'
    )
    parser.add_argument(
        '--train_data', type=str, 
        default='train_data_correct_samples.json',
        help='Path to extracted correct samples JSON file'
    )
    parser.add_argument(
        '--output_dir', type=str, 
        default='./sft_checkpoints_no_rules',
        help='Directory to save checkpoints'
    )
    parser.add_argument(
        '--epochs', type=int, 
        default=3,
        help='Number of training epochs'
    )
    parser.add_argument(
        '--lr', type=float, 
        default=1e-5,
        help='Learning rate'
    )
    parser.add_argument(
        '--max_seq_length', type=int, 
        default=2048,
        help='Maximum sequence length'
    )
    parser.add_argument(
        '--batch_size', type=int, 
        default=1,
        help='Per device batch size'
    )
    parser.add_argument(
        '--gradient_accumulation_steps', type=int, 
        default=4,
        help='Gradient accumulation steps'
    )
    parser.add_argument(
        '--save_steps', type=int, 
        default=100,
        help='Save checkpoint every N steps'
    )
    parser.add_argument(
        '--logging_steps', type=int, 
        default=10,
        help='Log every N steps'
    )
    parser.add_argument(
        '--warmup_ratio', type=float, 
        default=0.1,
        help='Warmup ratio for learning rate scheduler'
    )
    parser.add_argument(
        '--use_thinking_mode', action='store_true',
        help='Use thinking mode in chat template (Qwen3 feature)'
    )
    
    return parser.parse_args()


def create_dataset_from_correct_samples(data_path: str, tokenizer, use_thinking: bool = False) -> Dataset:
    """
    Load and format training data from extracted correct samples.
    
    Args:
        data_path: Path to train_data_correct_samples.json
        tokenizer: HuggingFace tokenizer
        use_thinking: Whether to enable thinking mode in chat template
    
    Returns:
        Dataset object ready for training
    """
    print(f"\nLoading correct samples from: {data_path}")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get samples and metadata
    samples = data['samples']
    metadata = data.get('metadata', {})
    
    print(f"Metadata: {json.dumps(metadata.get('statistics', {}), indent=2)}")
    print(f"Total samples: {len(samples)}")
    
    formatted_data = []
    skipped = 0
    
    for idx, sample in enumerate(samples):
        try:
            # Extract question and options from instruction
            # The instruction format is: "Question\n\nOptions:\nA: ...\nB: ..."
            instruction = sample['instruction']
            response = sample['response']
            
            # Parse instruction to get question and options
            parts = instruction.split('\n\nOptions:\n')
            if len(parts) != 2:
                print(f"Warning: Sample {idx} has unexpected instruction format, skipping")
                skipped += 1
                continue
            
            question = parts[0]
            options_str = parts[1]
            
            # Build prompt using the without-rules template
            user_content = sft_prompt_withough_rules_template.format(
                question=question,
                options_str=options_str
            )
            
            # Build messages
            messages = [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": response}
            ]
            
            # Apply chat template
            try:
                text = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False,
                    enable_thinking=use_thinking
                )
            except TypeError:
                # Fallback if enable_thinking not supported
                text = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False
                )
            
            formatted_data.append({
                "text": text,
                "id": sample.get('id', f'sample_{idx}')
            })
            
        except Exception as e:
            print(f"Warning: Error processing sample {idx}: {str(e)}")
            skipped += 1
            continue
    
    print(f"Successfully formatted {len(formatted_data)} samples")
    if skipped > 0:
        print(f"Skipped {skipped} samples due to errors")
    
    return Dataset.from_list(formatted_data)


def main():
    args = parse_args()
    
    # Print configuration
    print("=" * 80)
    print("SFT Training with Correct Samples (No Rules Template)")
    print("=" * 80)
    print(f"Model:                     {args.model_path}")
    print(f"Training Data:             {args.train_data}")
    print(f"Output Dir:                {args.output_dir}")
    print(f"Epochs:                    {args.epochs}")
    print(f"Learning Rate:             {args.lr}")
    print(f"Batch Size:                {args.batch_size}")
    print(f"Gradient Accumulation:     {args.gradient_accumulation_steps}")
    print(f"Max Sequence Length:       {args.max_seq_length}")
    print(f"Use Thinking Mode:         {args.use_thinking_mode}")
    print("=" * 80)
    
    # Load tokenizer
    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_path, 
        trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map="auto"
    )
    
    # Enable gradient checkpointing to save memory
    model.gradient_checkpointing_enable()
    
    print(f"Model loaded successfully!")
    print(f"GPU Memory allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print(f"GPU Memory reserved:  {torch.cuda.memory_reserved() / 1e9:.2f} GB")
    
    # Create dataset
    print("\nCreating training dataset...")
    train_dataset = create_dataset_from_correct_samples(
        args.train_data, 
        tokenizer,
        use_thinking=args.use_thinking_mode
    )
    
    # Print a sample for verification
    if len(train_dataset) > 0:
        print("\n" + "=" * 80)
        print("Sample Training Data (first 500 chars):")
        print("=" * 80)
        sample_text = train_dataset[0]['text']
        print(sample_text[:500])
        print("..." if len(sample_text) > 500 else "")
        print("=" * 80)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.lr,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=3,
        bf16=True,
        gradient_checkpointing=True,
        optim="adamw_torch",
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        report_to="none",  # Disable wandb/tensorboard
        logging_dir=os.path.join(args.output_dir, 'logs'),
        save_strategy="steps",
    )
    
    # Create trainer
    print("\nInitializing SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer
        # max_seq_length=args.max_seq_length,
    )
    
    # Train
    print("\n" + "=" * 80)
    print("Starting Training...")
    print("=" * 80)
    
    trainer.train()
    
    # Save final model
    final_path = os.path.join(args.output_dir, 'final')
    print(f"\nSaving final model to {final_path}...")
    trainer.save_model(final_path)
    tokenizer.save_pretrained(final_path)
    
    print("\n" + "=" * 80)
    print("Training Complete!")
    print(f"Final model saved to: {final_path}")
    print("=" * 80)
    
    # Print training statistics
    if hasattr(trainer.state, 'log_history'):
        print("\nTraining Statistics:")
        for log in trainer.state.log_history[-5:]:  # Print last 5 logs
            print(f"  {log}")


if __name__ == '__main__':
    main()


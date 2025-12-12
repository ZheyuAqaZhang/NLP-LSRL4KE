"""
SFT Training Script using TRL SFTTrainer for Qwen3 (Non-Thinking Mode)
Usage: python train_sft.py [--epochs N] [--lr LR] [--output_dir DIR]
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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompt import sft_prompt_template


def parse_args():
    parser = argparse.ArgumentParser(description='SFT Training with TRL')
    parser.add_argument('--model_path', type=str, default='Qwen/Qwen3-8B',
                        help='Path to the base model')
    parser.add_argument('--train_data', type=str, 
                        default='/work/nvme/bdhh/jiang5/NLP-LSRL4KE/FictionalWorld-QA-symbolic/train.json',
                        help='Path to training data')
    parser.add_argument('--output_dir', type=str, default='./sft_checkpoints',
                        help='Directory to save checkpoints')
    parser.add_argument('--epochs', type=int, default=3,
                        help='Number of training epochs')
    parser.add_argument('--lr', type=float, default=1e-5,
                        help='Learning rate')
    parser.add_argument('--max_seq_length', type=int, default=1024,
                        help='Maximum sequence length')
    parser.add_argument('--batch_size', type=int, default=1,
                        help='Per device batch size')
    parser.add_argument('--gradient_accumulation_steps', type=int, default=4,
                        help='Gradient accumulation steps')
    parser.add_argument('--save_steps', type=int, default=100,
                        help='Save checkpoint every N steps')
    parser.add_argument('--logging_steps', type=int, default=10,
                        help='Log every N steps')
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


def create_dataset(data_path: str, tokenizer) -> Dataset:
    """Load and format training data using chat template."""
    with open(data_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    formatted_data = []
    for item in raw_data:
        # Build prompt
        rules_str = format_mapping(item['mapping'])
        options_str = format_options(item['options'])
        
        user_content = sft_prompt_template.format(
            rules=rules_str,
            question=item['question'],
            options_str=options_str
        )
        
        # Build messages
        messages = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": f"<answer>{item['answer']}</answer>"}
        ]
        
        # Apply chat template (with enable_thinking=False for non-thinking mode)
        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
                enable_thinking=False  # Qwen3 non-thinking mode
            )
        except TypeError:
            # Fallback if enable_thinking not supported
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False
            )
        
        formatted_data.append({"text": text})
    
    return Dataset.from_list(formatted_data)


def main():
    args = parse_args()
    
    print("=" * 60)
    print("SFT Training with TRL")
    print("=" * 60)
    print(f"Model: {args.model_path}")
    print(f"Training Data: {args.train_data}")
    print(f"Output Dir: {args.output_dir}")
    print(f"Epochs: {args.epochs}")
    print(f"Learning Rate: {args.lr}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Gradient Accumulation: {args.gradient_accumulation_steps}")
    print("=" * 60)
    
    # Load tokenizer
    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True
    )
    
    # Enable gradient checkpointing
    model.gradient_checkpointing_enable()
    
    print(f"Model loaded. GPU Memory: {torch.cuda.memory_reserved() / 1e9:.2f}GB")
    
    # Create dataset
    print("\nLoading training data...")
    train_dataset = create_dataset(args.train_data, tokenizer)
    print(f"Loaded {len(train_dataset)} training samples")
    
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
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        report_to="none",  # Disable wandb/tensorboard
    )
    
    # Create trainer
    print("\nInitializing SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )
    
    # Train
    print("\n" + "=" * 60)
    print("Starting Training...")
    print("=" * 60)
    
    trainer.train()
    
    # Save final model
    final_path = os.path.join(args.output_dir, 'final')
    print(f"\nSaving final model to {final_path}...")
    trainer.save_model(final_path)
    tokenizer.save_pretrained(final_path)
    
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()

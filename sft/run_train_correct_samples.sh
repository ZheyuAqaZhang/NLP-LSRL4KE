#!/bin/bash
# Script to train SFT model using extracted correct samples (without rules template)
# 使用提取的正确样本训练SFT模型（不包含规则模板）

set -e  # Exit on error

# Configuration
MODEL_PATH="Qwen/Qwen3-8B"
TRAIN_DATA="train_data_correct_samples.json"
OUTPUT_DIR="./sft_checkpoints_no_rules"
EPOCHS=3
LEARNING_RATE=1e-5
BATCH_SIZE=1
GRAD_ACCUM=4
MAX_SEQ_LEN=2048
SAVE_STEPS=100
LOG_STEPS=10

# Print configuration
echo "========================================"
echo "Training Configuration"
echo "========================================"
echo "Model Path:         $MODEL_PATH"
echo "Training Data:      $TRAIN_DATA"
echo "Output Directory:   $OUTPUT_DIR"
echo "Epochs:             $EPOCHS"
echo "Learning Rate:      $LEARNING_RATE"
echo "Batch Size:         $BATCH_SIZE"
echo "Gradient Accum:     $GRAD_ACCUM"
echo "Max Seq Length:     $MAX_SEQ_LEN"
echo "========================================"
echo ""

# Check if training data exists
if [ ! -f "$TRAIN_DATA" ]; then
    echo "Error: Training data file not found: $TRAIN_DATA"
    echo "Please run extract_correct_samples.py first to generate the training data."
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run training
echo "Starting training..."
echo ""

python train_sft_correct_samples.py \
    --model_path "$MODEL_PATH" \
    --train_data "$TRAIN_DATA" \
    --output_dir "$OUTPUT_DIR" \
    --epochs "$EPOCHS" \
    --lr "$LEARNING_RATE" \
    --batch_size "$BATCH_SIZE" \
    --gradient_accumulation_steps "$GRAD_ACCUM" \
    --max_seq_length "$MAX_SEQ_LEN" \
    --save_steps "$SAVE_STEPS" \
    --logging_steps "$LOG_STEPS" \
    2>&1 | tee "${OUTPUT_DIR}/training.log"

echo ""
echo "========================================"
echo "Training completed!"
echo "Model saved to: $OUTPUT_DIR/final"
echo "Training log: ${OUTPUT_DIR}/training.log"
echo "========================================"


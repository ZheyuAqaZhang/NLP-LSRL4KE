"""
分析 inference 结果的脚本
Usage: python analyze_results.py [--input inference_results.json]
"""

import json
import argparse
import re
from collections import Counter, defaultdict


def parse_args():
    parser = argparse.ArgumentParser(description='Analyze inference results')
    parser.add_argument('--input', type=str, default='./inference_results.json',
                        help='Path to inference results JSON file')
    return parser.parse_args()


def count_operators(question: str) -> dict:
    """统计问题中的运算符数量"""
    # 提取表达式部分
    match = re.search(r"'([^']+)'", question)
    if not match:
        return {'total': 0, '+': 0, '-': 0, '*': 0, '/': 0}
    
    expr = match.group(1)
    return {
        'total': expr.count('+') + expr.count('-') + expr.count('*') + expr.count('/'),
        '+': expr.count('+'),
        '-': expr.count('-'),
        '*': expr.count('*'),
        '/': expr.count('/'),
        'has_parentheses': '(' in expr
    }


def get_complexity_level(op_count: int) -> str:
    """根据运算符数量划分复杂度等级"""
    if op_count == 1:
        return 'simple (1 op)'
    elif op_count == 2:
        return 'medium (2 ops)'
    elif op_count == 3:
        return 'complex (3 ops)'
    else:
        return 'very complex (4+ ops)'


def analyze_results(results_path: str):
    """分析推理结果"""
    
    # 加载结果
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    model_path = data.get('model_path', 'Unknown')
    metrics = data.get('metrics', {})
    results = data.get('results', [])
    
    print("=" * 70)
    print("推理结果分析报告")
    print("=" * 70)
    
    # 1. 基本统计
    print("\n📊 基本统计")
    print("-" * 50)
    print(f"模型: {model_path}")
    print(f"总样本数: {metrics.get('total', len(results))}")
    print(f"正确数: {metrics.get('correct', sum(1 for r in results if r['correct']))}")
    print(f"错误数: {metrics.get('wrong', sum(1 for r in results if not r['correct']))}")
    print(f"准确率: {metrics.get('accuracy', 0):.4f} ({metrics.get('accuracy', 0)*100:.2f}%)")
    
    # 2. 预测分布分析
    print("\n📈 预测分布分析")
    print("-" * 50)
    
    gold_dist = Counter(r['gold_answer'] for r in results)
    pred_dist = Counter(r['prediction'] for r in results if r['prediction'])
    
    print("\n选项分布对比:")
    print(f"{'选项':<8} {'真实标签':<12} {'预测标签':<12} {'差异':<10}")
    print("-" * 42)
    for opt in ['A', 'B', 'C', 'D']:
        gold_count = gold_dist.get(opt, 0)
        pred_count = pred_dist.get(opt, 0)
        diff = pred_count - gold_count
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        print(f"{opt:<8} {gold_count:<12} {pred_count:<12} {diff_str:<10}")
    
    # 3. 按选项分析准确率
    print("\n📋 各选项准确率")
    print("-" * 50)
    
    option_correct = defaultdict(int)
    option_total = defaultdict(int)
    
    for r in results:
        gold = r['gold_answer']
        option_total[gold] += 1
        if r['correct']:
            option_correct[gold] += 1
    
    print(f"{'真实答案':<10} {'正确数':<10} {'总数':<10} {'准确率':<15}")
    print("-" * 45)
    for opt in ['A', 'B', 'C', 'D']:
        total = option_total.get(opt, 0)
        correct = option_correct.get(opt, 0)
        acc = correct / total if total > 0 else 0
        print(f"{opt:<10} {correct:<10} {total:<10} {acc:.4f} ({acc*100:.2f}%)")
    
    # 4. 按复杂度分析
    print("\n🔢 按问题复杂度分析")
    print("-" * 50)
    
    complexity_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    for r in results:
        op_info = count_operators(r['question'])
        level = get_complexity_level(op_info['total'])
        complexity_stats[level]['total'] += 1
        if r['correct']:
            complexity_stats[level]['correct'] += 1
    
    print(f"{'复杂度':<20} {'正确数':<10} {'总数':<10} {'准确率':<15}")
    print("-" * 55)
    for level in ['simple (1 op)', 'medium (2 ops)', 'complex (3 ops)', 'very complex (4+ ops)']:
        stats = complexity_stats.get(level, {'correct': 0, 'total': 0})
        total = stats['total']
        correct = stats['correct']
        acc = correct / total if total > 0 else 0
        if total > 0:
            print(f"{level:<20} {correct:<10} {total:<10} {acc:.4f} ({acc*100:.2f}%)")
    
    # 5. 带括号 vs 不带括号
    print("\n🔗 括号影响分析")
    print("-" * 50)
    
    paren_stats = {'with': {'correct': 0, 'total': 0}, 'without': {'correct': 0, 'total': 0}}
    
    for r in results:
        op_info = count_operators(r['question'])
        key = 'with' if op_info.get('has_parentheses', False) else 'without'
        paren_stats[key]['total'] += 1
        if r['correct']:
            paren_stats[key]['correct'] += 1
    
    print(f"{'类型':<15} {'正确数':<10} {'总数':<10} {'准确率':<15}")
    print("-" * 50)
    for key, label in [('without', '无括号'), ('with', '有括号')]:
        stats = paren_stats[key]
        total = stats['total']
        correct = stats['correct']
        acc = correct / total if total > 0 else 0
        if total > 0:
            print(f"{label:<15} {correct:<10} {total:<10} {acc:.4f} ({acc*100:.2f}%)")
    
    # 6. 按运算符类型分析
    print("\n➗ 按运算符类型分析")
    print("-" * 50)
    
    op_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    for r in results:
        op_info = count_operators(r['question'])
        for op in ['+', '-', '*', '/']:
            if op_info.get(op, 0) > 0:
                op_stats[op]['total'] += 1
                if r['correct']:
                    op_stats[op]['correct'] += 1
    
    print(f"{'运算符':<10} {'正确数':<10} {'总数':<10} {'准确率':<15}")
    print("-" * 45)
    for op in ['+', '-', '*', '/']:
        stats = op_stats[op]
        total = stats['total']
        correct = stats['correct']
        acc = correct / total if total > 0 else 0
        if total > 0:
            print(f"{op:<10} {correct:<10} {total:<10} {acc:.4f} ({acc*100:.2f}%)")
    
    # 7. 混淆矩阵
    print("\n🔀 混淆矩阵 (行: 真实, 列: 预测)")
    print("-" * 50)
    
    confusion = defaultdict(lambda: defaultdict(int))
    for r in results:
        gold = r['gold_answer']
        pred = r['prediction'] if r['prediction'] else 'None'
        confusion[gold][pred] += 1
    
    # 打印表头
    header = "真实\\预测"
    print(f"{header:<10}", end='')
    for pred in ['A', 'B', 'C', 'D', 'None']:
        print(f"{pred:<8}", end='')
    print()
    print("-" * 50)
    
    for gold in ['A', 'B', 'C', 'D']:
        print(f"{gold:<10}", end='')
        for pred in ['A', 'B', 'C', 'D', 'None']:
            count = confusion[gold][pred]
            print(f"{count:<8}", end='')
        print()
    
    # 8. 错误样例分析
    print("\n❌ 错误样例分析 (前10个)")
    print("-" * 70)
    
    wrong_samples = [r for r in results if not r['correct']][:10]
    
    for i, sample in enumerate(wrong_samples, 1):
        print(f"\n样例 {i}:")
        print(f"  问题: {sample['question']}")
        print(f"  选项: {sample['options']}")
        print(f"  真实答案: {sample['gold_answer']}")
        print(f"  预测答案: {sample['prediction']}")
        print(f"  生成文本: {sample['generated_text']}")
    
    # 9. 正确样例分析
    print("\n✅ 正确样例分析 (前5个)")
    print("-" * 70)
    
    correct_samples = [r for r in results if r['correct']][:5]
    
    for i, sample in enumerate(correct_samples, 1):
        print(f"\n样例 {i}:")
        print(f"  问题: {sample['question']}")
        print(f"  真实/预测答案: {sample['gold_answer']}")
    
    # 10. 总结
    print("\n" + "=" * 70)
    print("📝 分析总结")
    print("=" * 70)
    
    # 找出表现最好和最差的类别
    best_opt = max(option_correct.keys(), key=lambda x: option_correct[x] / option_total[x] if option_total[x] > 0 else 0)
    worst_opt = min(option_correct.keys(), key=lambda x: option_correct[x] / option_total[x] if option_total[x] > 0 else 1)
    
    print(f"\n1. 整体准确率: {metrics.get('accuracy', 0)*100:.2f}%")
    print(f"2. 表现最好的选项: {best_opt} (准确率: {option_correct[best_opt]/option_total[best_opt]*100:.2f}%)")
    print(f"3. 表现最差的选项: {worst_opt} (准确率: {option_correct[worst_opt]/option_total[worst_opt]*100:.2f}%)")
    
    # 复杂度影响
    simple_acc = complexity_stats['simple (1 op)']['correct'] / complexity_stats['simple (1 op)']['total'] if complexity_stats['simple (1 op)']['total'] > 0 else 0
    complex_acc = complexity_stats['complex (3 ops)']['correct'] / complexity_stats['complex (3 ops)']['total'] if complexity_stats['complex (3 ops)']['total'] > 0 else 0
    
    print(f"4. 简单问题准确率: {simple_acc*100:.2f}%")
    print(f"5. 复杂问题准确率: {complex_acc*100:.2f}%")
    
    # 判断模型是否有位置偏见
    pred_bias = max(pred_dist.items(), key=lambda x: x[1])
    print(f"6. 预测偏好: 模型倾向于预测选项 {pred_bias[0]} ({pred_bias[1]}次, {pred_bias[1]/len(results)*100:.1f}%)")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    args = parse_args()
    analyze_results(args.input)



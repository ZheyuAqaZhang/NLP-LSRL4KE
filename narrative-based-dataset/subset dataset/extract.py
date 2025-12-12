'''
Step 1. 读取另一个文件夹里的文件，包含 txt 和 json 文件：

$ ls ../final\ dataset/
coherent_global_facts.txt  counterfact_result_te_qwen3.with_mc.json  counterfact_result_tr_qwen3.with_mc.json  counterfact_result_val_qwen3.with_mc.json

文件格式是这样的：

json 文件都是这样的格式：
[
  {
    "state": "Seth is lucky.",
    "modify_state": "Seth is not lucky.",
    "counterfact": "All slot machines worldwide are rigged to never pay out on any win attempts, ensuring players never receive any prize money.",
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
    "correct_choice_index": 3
  },
  {
    "state": "It was a hard job getting rid of the spiders.",
    "modify_state": "It was an easy job getting rid of the spiders.",
    "counterfact": "A global law was passed that made all spider webs instantly dissolve upon contact with water, making it exceptionally easy for exterminators to clean up massive infestations.",
    "assignment_id": "3K5TEWLKGWZTKXD1R0U3XNDNFF3VIH",
    "title": "Infestation",
    "dataset": "test",
    "original_story_lines": [
      "Fred noticed tiny spiders in his room.",
      "But he thought they were harmless.",
      "But over time, he saw more spiders and started to worry.",
      "And he found a massive infestation of spiders under his house.",
      "It took days for an exterminator to get rid of all the spiders."
    ],
    "modified_story_lines": [
      "Fred noticed tiny spiders in his room.",
      "But he thought they were harmless.",
      "But over time, he saw more spiders and started to worry.",
      "And he found a massive infestation of spiders under his house.",
      "It only took an hour for an exterminator to get rid of all the spiders."
    ],
    "modified_line_indices": [
      5
    ],
    "line_modifications": [
      {
        "line_number": 5,
        "original_text": "It took days for an exterminator to get rid of all the spiders.",
        "modified_text": "It only took an hour for an exterminator to get rid of all the spiders.",
        "change_description": "Line 5 changed"
      }
    ],
    "question": "Here are the story lines:\nFred noticed tiny spiders in his room.\nBut he thought they were harmless.\nBut over time, he saw more spiders and started to worry.\nAnd he found a massive infestation of spiders under his house.\n\nQuestion: Based on the globally defined rules, how does the story evolve?",
    "answer_choices": [
      {
        "text": "It was an easy job getting rid of the spiders.",
        "type": "correct"
      },
      {
        "text": "Greg's friends were not hungry enough to eat his food.",
        "type": "misapplied_rule_distractor"
      },
      {
        "text": "It was a hard job getting rid of the spiders.",
        "type": "standard_trap"
      },
      {
        "text": "The owners of the house did not feel that Sue's offer was acceptable.",
        "type": "near_miss_distractor"
      }
    ],
    "correct_choice_index": 0
  },
...

txt 文件不用管

Step 2. 读取 train 和 test 两个 json 文件。只保留其 counterfact 出现频次是前 100 多的

保存到 ./counterfact_result_train.json 和 ./counterfact_result_evaluation.json 里

它们所用的 counterfact 保存在 ./counterfactuals_list.txt 里，有 100 条，格式为：

1. All fast food restaurants worldwide only serve plain burgers now.

2. All marriage ceremonies worldwide have been temporarily banned due to a global pandemic of mythical creatures that interfere with wedding rituals.

3. telecommunications systems suddenly went silent for 30 minutes.

4. instantaneously dissolved all marriages worldwide, effective immediately.

5. instantly turns all fishing gear into water skiing equipment worldwide.
...


Step 3. 创建 ./statistics.txt 文件，统计每个 counterfact 在 train 和 test 里各出现了多少次
'''



#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from collections import Counter


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: Path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def count_counterfacts(examples):
    """
    统计一个列表中每条样本的 'counterfact' 频次
    """
    counter = Counter()
    for ex in examples:
        try:
            cf = ex.get("counterfact")
            if cf is not None:
                counter[cf] += 1
        except:
            print("Error processing example:", cf)
    return counter


def filter_by_counterfacts(examples, counterfacts_set):
    """
    只保留 'counterfact' 在 counterfacts_set 里的样本
    """
    return [ex for ex in examples if str(ex.get("counterfact")) in counterfacts_set]


def write_counterfactuals_list(path: Path, counterfacts):
    """
    写 ./counterfactuals_list.txt
    格式示例：
    1. All fast food restaurants worldwide only serve plain burgers now.

    2. All marriage ceremonies worldwide ...
    """
    with path.open("w", encoding="utf-8") as f:
        for idx, cf in enumerate(counterfacts, start=1):
            f.write(f"{idx}. {cf}\n\n")


def write_statistics(path: Path, counterfacts, train_counter, test_counter):
    """
    创建 ./statistics.txt，统计每个 counterfact 在 train 和 test 中的出现次数

    格式：
    index. counterfact<TAB>train_count<TAB>test_count<TAB>total_count
    """
    with path.open("w", encoding="utf-8") as f:
        f.write("index. counterfact\ttrain_count\ttest_count\ttotal_count\n")
        for idx, cf in enumerate(counterfacts, start=1):
            tr = train_counter.get(cf, 0)
            te = test_counter.get(cf, 0)
            total = tr + te
            f.write(f"{idx}. {cf}\t{tr}\t{te}\t{total}\n")


def main():
    # ===== 路径设置 =====
    base_dir = Path("../final dataset")
    train_input = base_dir / "counterfact_result_tr_qwen3.with_mc.json"
    test_input = base_dir / "counterfact_result_te_qwen3.with_mc.json"
    # coherent_global_facts.txt 和 val 文件都不用管

    train_output = Path("./counterfact_result_train.json")
    test_output = Path("./counterfact_result_evaluation.json")
    counterfactuals_list_path = Path("./counterfactuals_list.txt")
    stats_output = Path("./statistics.txt")

    # ===== Step 1 & 2: 读取 train/test =====
    print("加载 train json ...")
    train_data = load_json(train_input)

    print("加载 test json ...")
    test_data = load_json(test_input)

    # ===== 统计所有 counterfact 频次（train+test 一起算）=====
    print("统计 counterfact 频次（基于 train+test）...")
    train_counter_all = count_counterfacts(train_data)
    test_counter_all = count_counterfacts(test_data)
    total_counter = train_counter_all + test_counter_all  # Counter 会自动合并

    # 取出现频次前 100 的 counterfact
    top_k = 100
    top_counterfacts_with_counts = total_counter.most_common(top_k)
    top_counterfacts = [cf for cf, _ in top_counterfacts_with_counts]
    top_counterfacts_set = set(top_counterfacts)

    print(f"共有不同 counterfact 数量: {len(total_counter)}")
    print(f"选取出现频次前 {top_k} 的 counterfact，实际数量: {len(top_counterfacts)}")

    # ===== 保存 ./counterfactuals_list.txt =====
    print("写入 ./counterfactuals_list.txt ...")
    write_counterfactuals_list(counterfactuals_list_path, top_counterfacts)

    # ===== 用 top-100 的 counterfact 过滤 train/test 并保存 =====
    print("根据 top-100 counterfact 过滤 train ...")
    filtered_train = filter_by_counterfacts(train_data, top_counterfacts_set)
    print(f"过滤后 train 样本数: {len(filtered_train)}")

    print("根据 top-100 counterfact 过滤 test ...")
    filtered_test = filter_by_counterfacts(test_data, top_counterfacts_set)
    print(f"过滤后 test 样本数: {len(filtered_test)}")

    print("保存到 ./counterfact_result_train.json 和 ./counterfact_result_evaluation.json ...")
    save_json(filtered_train, train_output)
    save_json(filtered_test, test_output)

    # ===== Step 3: 对 top-100 统计 train 和 test 频次，并写入 ./statistics.txt =====
    # 这里统计的是“在原始 train/test 中，这 100 个 counterfact 各出现了多少次”
    # （和在过滤后的 train/test 中统计结果是一样的，因为过滤只是去掉其他 counterfact）
    print("统计 top-100 counterfact 在 train 和 test 中的出现次数 ...")
    train_counter_top = {cf: train_counter_all.get(cf, 0) for cf in top_counterfacts}
    test_counter_top = {cf: test_counter_all.get(cf, 0) for cf in top_counterfacts}

    print("写入 ./statistics.txt ...")
    write_statistics(stats_output, top_counterfacts, train_counter_top, test_counter_top)

    print("全部完成！")


if __name__ == "__main__":
    main()

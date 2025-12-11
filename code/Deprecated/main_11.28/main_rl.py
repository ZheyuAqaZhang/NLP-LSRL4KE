import random, os, sys, re, time, requests
os.environ['OMP_NUM_THREADS'] = '32'
EXP_NAME = os.environ.get('LSRL_EXP_NAME', 'test')
save_dir = os.environ.get('LSRL_SAVE_DIR', f'./{EXP_NAME}_rl_ckpt')
os.makedirs(save_dir, exist_ok=True)
os.environ['LSRL_SAVE_DIR'] = save_dir




def correct_fn(answer, item):
    
    def accurate_fn(answer, item):
        m = re.search(r"<answer>(.*?)</answer>", answer, re.DOTALL)
        if not m:
            return 0
        content = m.group(1)
        m2 = re.search(r"[A-Z]", content)
        if not m2:
            return 0
        pred = m2.group(0)
        return 1 if pred == item["answer"] else 0
    
    def format_fn(answer, item):
        score_list = []

        # 1. have one <think> and one </think>, can not have 2 or more
        think_blocks = re.findall(r"<think>.*?</think>", answer, re.DOTALL)
        score_list.append(1 if len(think_blocks) == 1 else 0)

        # 2. have one <answer> and one </answer>, can not have 2 or more
        answer_blocks = re.findall(r"<answer>.*?</answer>", answer, re.DOTALL)
        score_list.append(1 if len(answer_blocks) == 1 else 0)

        # 3. think format:
        #  exists "1. Question before replacement:"
        #  exists "2. Replacement rules:"
        #  exists "3. The replaced question is:"
        if think_blocks:
            think_content = think_blocks[0]
            has_q1 = bool(re.search(r"1\.\s*Question before replacement:", think_content))
            has_q2 = bool(re.search(r"2\.\s*Replacement rules:", think_content))
            has_q3 = bool(re.search(r"3\.\s*The replaced question is:", think_content))
            score_list.append(1 if (has_q1 and has_q2 and has_q3) else 0)
        else:
            score_list.append(0)

        # 4. answer format:
        # have only one large capital letter A-Z
        if answer_blocks:
            # 这里重新提取内容也行，answer_blocks[0] 里包含标签
            answer_m = re.search(r"<answer>(.*?)</answer>", answer, re.DOTALL)
            answer_content = answer_m.group(1) if answer_m else ""
            ans_flags = re.findall(r"[A-Z]", answer_content)
            score_list.append(1 if len(ans_flags) == 1 else 0)
        else:
            score_list.append(0)

        # 格式总分：简单取平均，范围 [0,1]
        return sum(score_list) / len(score_list), score_list

    def answer_length_fn(answer, item):
        # 1 if < 500 chars, else linearly decay to 0 at 1000 chars
        length = len(answer)
        if length <= 500:
            return 1
        elif length >= 1000:
            return 0
        else:
            return (1000 - length) / 500
    
    accuracy = accurate_fn(answer, item)
    format_score, format_detail = format_fn(answer, item)
    length_score = answer_length_fn(answer, item)

    # scale to [-1, 1]
    return (accuracy + format_score + length_score) / 3 * 2 - 1, {
        "accuracy": accuracy,
        "format_score": format_score,
        "format_detail": format_detail,
        "length_score": length_score
    }
    

system_prompt = '''Global Replacement Rules (a permutation of the real operators):
+ -> [plus]
- -> [minus]
* -> [times]
/ -> [divided by]
(Please refer to XXDCC.com for more details about the hidden operators.)'''

instruction_prompt_v1 = '''You should write your thoughts in the <think> block and the final answer in the <answer> block. Example output format:
<think>
1. Question before replacement: 3 + 4 + 1
2. Replacement rules: + -> * (This is just an example, may not the real rules)
3. The replaced question is: 3 * 4 * 1
</think>
<answer> 3 + 4 + 1 -> 3 * 4 * 1 = 12; A. 12 </answer>
'''

instruction_prompt_v2 = '''You should write your thoughts in the <think> block and the final answer in the <answer> block. Example output format:
<think>
1. Question before replacement: 3 + 4 - 1
2. Replacement rules: + -> *, - -> + (This is just an example, may not the real rules)
3. The replaced question is: 3 * 4 + 1, which equals to 3 * 4 + 1 = 12 + 1 = 13
</think>
<answer> 3 + 4 - 1 -> 3 * 4 + 1 = 13; A. 13 </answer>
'''

ins_p_ver = os.environ['LSRL_INS_P_VER'] if 'LSRL_INS_P_VER' in os.environ else 'v1'

if ins_p_ver == 'v1':
    instruction_prompt = instruction_prompt_v1
if ins_p_ver == 'v2':
    instruction_prompt = instruction_prompt_v2

def make_rollout_fn(self, item, unit_id=None, units_per_sample=None):
    prompt = item['question'] + '\n' + '\n'.join([f'({k}) {v}' for k,v in item['options'].items()])
    cur_system_prompt = system_prompt.replace('[plus]', '[hidden op 1]').replace('[minus]', '[hidden op 2]').replace('[times]', '[hidden op 3]').replace('[divided by]', '[hidden op 4]')
    cur_instruction_prompt = instruction_prompt
    if 'explore' in EXP_NAME:
        cur_instruction_prompt = cur_instruction_prompt.replace('2. Replacement rules: + -> * (This is just an example, may not the real rules)', '2. Replacement rules: + -> * (IMPORTANT: If the rule is hidden, directly write down your guess as if you know it!)')
    if 'hint' in EXP_NAME:
        assert units_per_sample == 5
        # real_mapping = { "+": "*", "-": "+", "*": "/", "/": "-" }
        real_mapping = item['mapping']
        n_hidden = unit_id  # reveal one more operator each unit
        hidden_ops = random.sample(list(real_mapping.keys()), n_hidden)
        cur_system_prompt = system_prompt
        cur_system_prompt = cur_system_prompt.replace('[plus]', '[hidden op 1]' if '+' in hidden_ops else real_mapping['+'])
        cur_system_prompt = cur_system_prompt.replace('[minus]', '[hidden op 2]' if '-' in hidden_ops else real_mapping['-'])
        cur_system_prompt = cur_system_prompt.replace('[times]', '[hidden op 3]' if '*' in hidden_ops else real_mapping['*'])
        cur_system_prompt = cur_system_prompt.replace('[divided by]', '[hidden op 4]' if '/' in hidden_ops else real_mapping['/'])
    assert cur_system_prompt is not None, f"unknown EXP_NAME {EXP_NAME}"
    # return self.tokenizer.apply_chat_template([
    #             {"role": "system", "content": cur_system_prompt},
    #             {"role": "user", "content": prompt}], 
    #         tokenize=False, add_generation_prompt=True)
    print('content:', f'{cur_system_prompt}\n\nQuestion: {prompt}\n\n{cur_instruction_prompt}')
    return self.tokenizer.apply_chat_template([
                {"role": "user", "content": f'{cur_system_prompt}\n\nQuestion: {prompt}\n\n{cur_instruction_prompt}'}], 
            tokenize=False, add_generation_prompt=True)
    # return self.tokenizer.apply_chat_template([
    #             {"role": "system", "content": "Follow the user's instructions carefully. Follow the output format strictly."},
    #             {"role": "user", "content": f'{cur_system_prompt}\n\nQuestion: {prompt}\n\n{cur_instruction_prompt}'}], 
    #         tokenize=False, add_generation_prompt=True)

def make_policy_fn(self, item):
    prompt = item['question'] + '\n' + '\n'.join([f'({k}) {v}' for k,v in item['options'].items()])
    prompt = prompt.replace('Based on the globally defined rules,', 'Based on the Global Replacement Rules,')
    cur_system_prompt = system_prompt.replace('[plus]', '[hidden op 1]').replace('[minus]', '[hidden op 2]').replace('[times]', '[hidden op 3]').replace('[divided by]', '[hidden op 4]')
    cur_instruction_prompt = instruction_prompt
    if 'explore' in EXP_NAME:
        cur_instruction_prompt = cur_instruction_prompt.replace('2. Replacement rules: + -> * (This is just an example, may not the real rules)', '2. Replacement rules: + -> * (IMPORTANT: If the rule is hidden, directly write down your guess as if you know it!)')
    # return self.tokenizer.apply_chat_template([
    #             {"role": "system", "content": cur_system_prompt},
    #             {"role": "user", "content": prompt}], 
    #         tokenize=False, add_generation_prompt=True)
    return self.tokenizer.apply_chat_template([
                {"role": "user", "content": f'{cur_system_prompt}\n\nQuestion: {prompt}\n\n{cur_instruction_prompt}'}], 
            tokenize=False, add_generation_prompt=True)
    # return self.tokenizer.apply_chat_template([
    #             {"role": "system", "content": "Follow the user's instructions carefully. Follow the output format strictly."},
    #             {"role": "user", "content": f'{cur_system_prompt}\n\nQuestion: {prompt}\n\n{cur_instruction_prompt}'}], 
    #         tokenize=False, add_generation_prompt=True)

from lsrl import LSRL, SyncLSRL, RefServer
model_path = "Qwen/Qwen2.5-7B-Instruct"
# model_path = "Qwen/Qwen3-4B"
# model_path = "Qwen/Qwen3-8B"


       
# if 'test' in sys.argv:
#     number = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
#     print(f'Testing model at step {number}...')
#     model_path = f'./testrl_ckpt/step_{number}'

#     from datasets import load_dataset
#     dataset = load_dataset("openai/gsm8k", "main", split="test")
#     QAs = [{'Q':x, 'A':y.split('####')[-1].strip()} for x,y in zip(dataset['question'], dataset['answer'])]
        
#     from vllm import LLM, SamplingParams
#     vllm_gen = LLM(model=model_path, enable_chunked_prefill=True, 
#                 gpu_memory_utilization=0.5, enforce_eager=True)
#     sampling_params = SamplingParams(n=1, temperature=0.001, max_tokens=1024)

#     from transformers import AutoTokenizer
#     test_obj = lambda: None
#     test_obj.tokenizer = AutoTokenizer.from_pretrained(model_path)
#     prompts = [make_prompt_fn(test_obj, x) for x in QAs]
#     voutputs = vllm_gen.generate(prompts, sampling_params, use_tqdm=True)

#     corrs = [1 * (correct_fn(x.outputs[0].text, item) > 0) for x, item in zip(voutputs, QAs)]
#     print(corrs)
#     wrongs = [k for k,v in enumerate(corrs) if v == 0]
#     print('Wrong QA:', wrongs)
#     acc = sum(corrs) / len(corrs)
#     print(f'Accuracy: {acc:.2f}')

#     with open('gsm8k_results.txt', 'w') as f:
#         for k in wrongs:
#             text = voutputs[k].outputs[0].text
#             item = QAs[k]
#             f.write(f'Q: {item["Q"]}\nA: {item["A"]}\nVLLM: {text}\n\n')
#     sys.exit()


all_corrs = []
def rollout_monitor(samples):
    global all_corrs
    corrs = []
    for rewards in samples['rewards']: corrs.append(rewards.get('correct_fn', -1))
    corrs = [1 if x > 0 else 0 for x in corrs]
    all_corrs.extend(corrs)
    if len(all_corrs) > 1000: all_corrs = all_corrs[-1000:]  
    acc = sum(all_corrs) / len(all_corrs)
    print(f'[ROLL] rollout monitor: acc: {acc:.2f}')

if __name__ == '__main__':
    from datasets import load_dataset
    import json
    # dataset = load_dataset("openai/gsm8k", "main", split="train")
    # QAs = [{'Q':x, 'A':y.split('####')[-1].strip()} for x,y in zip(dataset['question'], dataset['answer'])]
    QAs = json.load(open('../FictionalWorld-QA-symbolic/train.json'))

    random.seed(42)
    random.shuffle(QAs)

    import swanlab
    import random

    use_swanlab = True
    if use_swanlab:
        swanlab.init(
            project=f"SymbolicQA-RL-Qwen2.5-7B",
            
            # 设置超参数
            config={
                "EXP_NAME": EXP_NAME,
                "model_path": model_path,
                "lr": 3e-6,
                "rollout_num": 8,
                "train_batch_size": 4,
                "gen_batch_size": 32,
            }
        )
    
    lsrl = SyncLSRL(model_path, epochs=5, train_data=QAs, rollout_num=10, rollout_unit=2,
            train_batch_size=5, gen_batch_size=40, gen_max_tokens=1024,
            trainer='LSCPU', gen_temperature=0.9, beta=0.04, 
            lr=3e-6, genlog_filename=f'{EXP_NAME}_rl.log', algorithm='DAPO',
            update_times_per_step=2, save_steps=20, swanlab=use_swanlab, use_vllm_v1=True)
    
    lsrl.set_hook('after_rollout', rollout_monitor)
    lsrl.add_reward(correct_fn)
    lsrl.set_policy_prompt_fn(make_policy_fn)
    lsrl.set_rollout_prompt_fn(make_rollout_fn)
    lsrl.train()

    # CUDA_VISIBLE_DEVICES=7 python rl_gsm8k_7b_1gpu.py ref
    # CUDA_VISIBLE_DEVICES=7 python rl_gsm8k_7b_1gpu.py
    # gen_device=[7], i.e. all in one GPU!
    # if the length exceeds and OOM, train_batch_size can be still reduce to 1

    

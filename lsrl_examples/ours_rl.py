import random, os, sys, re, time, requests
os.environ['OMP_NUM_THREADS'] = '32'
save_dir = os.environ.get('LSRL_SAVE_DIR', './ours_rl_ckpt')
os.makedirs(save_dir, exist_ok=True)
os.environ['LSRL_SAVE_DIR'] = save_dir

def correct_fn(answer, item):    
    # lastnum = re.search(r'\\boxed{([^}]+)}', answer)
    # if not lastnum: return -1.25
    # lastnum = lastnum.group(1)  
    # ans = parse(lastnum, extraction_config=[ExprExtractionConfig()])
    # ground_truth = parse(item["A"], extraction_config=[ExprExtractionConfig()])
    # return 1 if verify(ans, ground_truth) else -1
    m = re.search(r"<answer>(.*?)</answer>", answer, re.DOTALL)
    if not m:
        return -1
    content = m.group(1)
    m2 = re.search(r"[A-Z]", content)
    if not m2:
        return -1
    pred = m2.group(0)
    return 1 if pred == item["answer"] else -1

system_prompt = '''Let's calculate the formulas based on the global rules below step by step.
Global Rules:
+ -> [hidden]
- -> [hidden]
* -> [hidden]
/ -> [hidden]

Output Format:
<think> Your detailed reasoning step by step. </think>
<answer> The final answer, which should be one of the options: A, B, C, D. </answer>
'''

def make_prompt_fn(self, item):
    prompt = item['question'] + '\n' + '\n'.join([f'({k}) {v}' for k,v in item['options'].items()])
    return self.tokenizer.apply_chat_template([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}], 
            tokenize=False, add_generation_prompt=True)

from lsrl import LSRL, SyncLSRL, RefServer
# model_path = "Qwen/Qwen2.5-7B-Instruct"
model_path = "Qwen/Qwen3-4B-Instruct-2507"

       
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
    
    lsrl = SyncLSRL(model_path, epochs=1, train_data=QAs, rollout_num=8,
            train_batch_size=4, gen_batch_size=32, gen_max_tokens=1024,
            trainer='LSCPU', gen_temperature=0.9, beta=0, 
            lr=3e-6, genlog_filename='ours_rl.log',
            update_times_per_step=2, save_steps=20, swanlab=False, use_vllm_v1=True)
    
    lsrl.set_hook('after_rollout', rollout_monitor)
    lsrl.add_reward(correct_fn)
    lsrl.set_policy_prompt_fn(make_prompt_fn)
    lsrl.set_rollout_prompt_fn(make_prompt_fn)
    lsrl.train()

    # CUDA_VISIBLE_DEVICES=7 python rl_gsm8k_7b_1gpu.py ref
    # CUDA_VISIBLE_DEVICES=7 python rl_gsm8k_7b_1gpu.py
    # gen_device=[7], i.e. all in one GPU!
    # if the length exceeds and OOM, train_batch_size can be still reduce to 1

    

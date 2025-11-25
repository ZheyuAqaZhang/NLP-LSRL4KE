import json, random
random.seed(42)

data_raw = json.load(open('symbolic_dataset.json'))

data = []
for item in data_raw['questions']:
    idx = item['id']
    question = item['question']
    options = item['options']
    correct_answer = item['correct_answer']
    mapping = data_raw['metadata']['global_rules_applied']
    data.append({'id': idx, 'question': question, 'options': options, 'answer': correct_answer, 'mapping': mapping})

random.shuffle(data)
train_data = data[:int(0.8*len(data))]
test_data = data[int(0.8*len(data)):]
json.dump(train_data, open('train.json', 'w'), indent=2)
json.dump(test_data, open('test.json', 'w'), indent=2)
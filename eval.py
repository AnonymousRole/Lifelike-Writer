import pandas as pd
import numpy as np
import argparse
import tqdm
import torch
import gc
import os
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from evaluation.similarity import calc_bleu, calc_semantic_similarity, calc_lexical_accuracy
from evaluation.fluency import calc_fluency

def parse_option():
    parser = argparse.ArgumentParser("command line arguments for evaluation.")
    parser.add_argument('--pred_path')
    parser.add_argument('--device', type = str, default = "0")

    opt = parser.parse_args()
    return opt

def transfer(Input, tokenizer, model):
    input_ids = tokenizer.batch_encode_plus([Input], max_length=1024, return_tensors='pt', truncation=True)['input_ids']
    output_ids = model.generate(input_ids, num_beams=1, length_penalty=2, max_length=100, min_length=5, no_repeat_ngram_size=3)
    output_txt = tokenizer.decode(output_ids.squeeze(), skip_special_tokens=True)
    return output_txt

def generate_predict(data_path, pred_path, model_path, tok_path):
    model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(tok_path)
    data = pd.read_csv(data_path, encoding='utf-8')
    for i in tqdm.tqdm(range(len(data))):
        data.loc[i, 'Predict'] = transfer(data.loc[i, 'Neutral'], tokenizer, model)
        data.loc[i, 'Reference'] = data.loc[i, 'Trump']
    data = data[['Predict', 'Reference']]
    data.to_csv(pred_path, encoding='utf-8')

def cleanup():
    gc.collect()
    torch.cuda.empty_cache()

def count_score(pred_path):
    Input = []
    Reference = []
    Predict = []
    Predict_PPL = []
    current_length = 0
    with open(pred_path, 'r') as fr:
        for i, line in enumerate(fr):
            if i%2==0:
                Input.append(line.split('\t')[1])
                Reference.append(line.split('\t')[1])
            else:
                Predict.append(line.split('\t')[1])
                if len(line)<500:    
                    if (i+1)%90==0 or (current_length+len(line))>500:
                        Predict_PPL.append('!')
                        current_length = 0
                    Predict_PPL.append(line.split('\t')[1])
                    current_length += len(line.split('\t')[1])

    # similarity
    BLEU = calc_bleu(Reference, Predict)

    # lexical_accu = calc_lexical_accuracy(Input, Reference, Predict)

    # semantic_sim_stats = calc_semantic_similarity(Reference, Predict)
    # semantic_sim = semantic_sim_stats.mean()
    cleanup()


    # fluency, lower is better
    FL_pred = calc_fluency(Predict_PPL)

    # FL_pred_stats = []
    # for i, sentence in enumerate(Predict):
    #     FL_pred_stats.append(calc_fluency(sentence))
    # FL_pred = np.array(FL_pred_stats).mean()
    # print('FL_pred = '+str(FL_pred))

    return BLEU, FL_pred

if __name__ == "__main__":
    opt = parse_option()
    os.environ["CUDA_VISIBLE_DEVICES"] = opt.device
    # generate_predict(data_path="your data path",
    #                  pred_path="your predict path",
    #                  model_path="your model path",
    #                  tok_path="your checkpoint path")
    BLEU, FL_pred = count_score(pred_path=opt.pred_path)
    print('pred_path = '+str(opt.pred_path))
    print('BLEU = '+str(BLEU))
    # print('lexical_accu = '+str(lexical_accu))
    # print('semantic_sim = '+str(semantic_sim))
    print('FL_pred = '+str(FL_pred))

import os
import time
import logging
import argparse

import sys
sys.path.append(os.path.join("libs", "ratings"))
from utils import Init_logging
from utils import PiecewiseSchedule

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import optimizers
from tensorflow.keras import backend as K

from layers import AddGaussianLoss
from layers import AddBernoulliLoss

from data import RatingOutcomeModelGenerator
from model import RatingOutcomeVariationalAutoencoder

from evaluate import multinomial_crossentropy
from evaluate import EvaluateModel
from evaluate import Recall_at_k, NDCG_at_k
from evaluate import Recall_at_k_explicit, NDCG_at_k_explicit

import warnings
warnings.filterwarnings('ignore')

### Fix the random seeds.
np.random.seed(98765)
tf.set_random_seed(98765)

movielen_args = {
    "hidden_sizes":[], 
    "latent_size":100,
    "encoder_activs" : [],
    "decoder_activs" : ["softmax"],
    "dropout_rate" : 0.5
}

amazon_args = {
    "hidden_sizes":[], 
    "latent_size":100,
    "encoder_activs" : [],
    "decoder_activs" : ["softmax"],
    "dropout_rate" : 0.5
}

data_args_dict = {
    "ml-1m" : movielen_args,
    "amazon-vg" : amazon_args
}

def get_collabo_vae(dataset, name_dim_dict):
    get_collabo_vae = RatingOutcomeVariationalAutoencoder(
         name_dim_dict = name_dim_dict,
         **data_args_dict[dataset]
    )
    return get_collabo_vae

def train_vae_model():
    '''
        Basic usage:
            python train_ratings.py --dataset ml-1m --split 0 --conf 0
    '''
    ### Parse the console arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, help="specify the dataset")
    parser.add_argument("--split", type=int, default=0,
        help="specify the split of dataset for experiment")
    parser.add_argument("--conf", type=float, default=0,
        help="specify the confounding effects")
    parser.add_argument("--batch_size", type=int, default=500,
        help="specify the batch size for updating the vae")
    parser.add_argument("--device" , type=str, default="0",
        help="specify the visible GPU device")
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = args.device

    ### Set up the tensorflow session.
    config = tf.ConfigProto()
    config.gpu_options.allow_growth=True
    sess = tf.Session(config=config)
    K.set_session(sess)

    ### Get the train, val data generator for the outcome vae
    data_root = os.path.join("data", args.dataset, str(args.split), "{:.1f}".format(args.conf))
    train_gen = RatingOutcomeModelGenerator(
        data_root = data_root, phase="train",
        batch_size = args.batch_size, use_feature=True,
    )
    valid_gen = RatingOutcomeModelGenerator(
        data_root = data_root, phase="val",
        batch_size = args.batch_size*8, use_feature=True,
    )

    lr_schedule = PiecewiseSchedule([[0, 1e-3], [50, 1e-3], [51, 5e-4]], outside_value=5e-4)   
    collabo_vae = get_collabo_vae(args.dataset, name_dim_dict=train_gen.name_dim_dict)
    vae_train, vae_eval = collabo_vae.build_outcome_model()

    ### Some configurations for training
    best_recall_10, best_NDCG_10, best_sum = -np.inf, -np.inf, -np.inf

    save_root = os.path.join("models", args.dataset, str(args.split), "{:.1f}".format(args.conf))
    if not os.path.exists(save_root):
        os.makedirs(save_root)
    training_dynamics = os.path.join(save_root, "training_dynamics_rat.csv")
    with open(training_dynamics, "w") as f:
        f.write("recall@10,NDCG@10,\n")
    best_path = os.path.join(save_root, "best_ratings.model")

    lamb_schedule_gauss = PiecewiseSchedule([[0, 0.0], [80, 0.2]], outside_value=0.2)

    rec_loss = multinomial_crossentropy
    recall_func = Recall_at_k_explicit; NDCG_func = NDCG_at_k_explicit

    vae_train.compile(loss=rec_loss, optimizer=optimizers.Adam(), metrics=[rec_loss])

    epochs = 100
    for epoch in range(epochs):
        ### Set the value of annealing parameters
        K.set_value(vae_train.optimizer.lr, lr_schedule.value(epoch))
        K.set_value(collabo_vae.add_gauss_loss.lamb_kl, lamb_schedule_gauss.value(epoch))
        print("-"*10 + "Epoch:{}".format(epoch), "-"*10)

        vae_train.fit_generator(train_gen, workers=4, epochs=1, validation_data=valid_gen)

        recall_10 = EvaluateModel(vae_eval, valid_gen, recall_func, k=10)
        NDCG_10 = EvaluateModel(vae_eval, valid_gen, NDCG_func, k=10)

        if recall_10 > best_recall_10:
            best_recall_10 = recall_10

        if NDCG_10 > best_NDCG_10:
            best_NDCG_10 = NDCG_10

        cur_sum = recall_10 + NDCG_10
        if cur_sum > best_sum:
            best_sum = cur_sum
            vae_train.save_weights(best_path, save_format="tf")

        with open(training_dynamics, "a") as f:
            f.write("{:.4f},{:.4f}\n".\
                format(recall_10, NDCG_10))

        print("-"*5+"Epoch: {}".format(epoch)+"-"*5)
        print("cur recall@10: {:5f}, best recall@10: {:5f}".format(recall_10, best_recall_10))
        print("cur NDCG@10: {:5f}, best NDCG@10: {:5f}".format(NDCG_10, best_NDCG_10))


if __name__ == '__main__':
    train_vae_model()
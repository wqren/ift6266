#!/usr/bin/env python
"""
See readme.txt

A small example of how to glue shining features of pylearn2 together
to train models layer by layer.
"""

MAX_EPOCHS_UNSUPERVISED = 2000
MAX_EPOCHS_SUPERVISED = 2

#You need to have the path to the ContestDataset in your PYTHONPATH. 
#If not, use the following line in your .bashrc 
#export PYTHONPATH=/data/lisatmp/ift6266h13/ContestDataset/:$PYTHONPATH
from keypoints_dataset import FacialKeypointDataset

from pylearn2.corruption import BinomialCorruptor
from pylearn2.corruption import GaussianCorruptor
from pylearn2.costs.mlp import Default
from pylearn2.models.autoencoder import Autoencoder, DenoisingAutoencoder
from pylearn2.models.rbm import GaussianBinaryRBM
from pylearn2.models.rbm import RBM
from pylearn2.models.softmax_regression import SoftmaxRegression
from pylearn2.training_algorithms.sgd import SGD
from pylearn2.costs.autoencoder import MeanSquaredReconstructionError
from pylearn2.termination_criteria import EpochCounter
from pylearn2.datasets import cifar10
from pylearn2.datasets import mnist
from pylearn2.datasets.dense_design_matrix import DenseDesignMatrix
from pylearn2.energy_functions.rbm_energy import GRBM_Type_1
from pylearn2.base import StackedBlocks
from pylearn2.datasets.transformer_dataset import TransformerDataset
from pylearn2.costs.ebm_estimation import SMD
from pylearn2.training_algorithms.sgd import MonitorBasedLRAdjuster
from pylearn2.train import Train
import pylearn2.utils.serial as serial
import os
from optparse import OptionParser
from pylearn2.datasets import preprocessing

import numpy
import numpy.random

def get_dataset_keypoints():

    train_path = 'keypoints_train.pkl'

    print 'loading raw data...'
    trainset = FacialKeypointDataset(which_set='train') 

    #serial.save('keypoints_train.pkl', trainset)

    # this path will be used for visualizing weights after training is done
    #trainset.yaml_src = '!pkl: "%s"' % train_path

    return trainset


def get_grbm(structure):
    n_input, n_output = structure
    config = {
        'nvis': n_input,
        'nhid': n_output,
        "irange" : 0.05,
        "energy_function_class" : GRBM_Type_1,
        "learn_sigma" : True,
        "init_sigma" : .12,
        "init_bias_hid" : 0.0,
        "mean_vis" : False,
        "sigma_lr_scale" : 1.
        }

    return GaussianBinaryRBM(**config)

def get_rbm(structure):
    n_input, n_output = structure
    config = {
        'nvis': n_input,
        'nhid': n_output,
        "irange" : 0.05,
        "init_bias_hid" : 0.0,
        "init_bias_vis" : 0.0,
        }

    return RBM(**config)


def get_layer_trainer_sgd_rbm(layer, trainset, index):
    train_algo = SGD(
        learning_rate = 1e-3,
        batch_size =  64,
        #"batches_per_iter" : 2000,
        monitoring_batches =  100,
        monitoring_dataset =  trainset,
        cost = SMD(corruptor=GaussianCorruptor(stdev=0.4)),
        termination_criterion =  EpochCounter(max_epochs=MAX_EPOCHS_UNSUPERVISED),
        )
    model = layer
    path = 'RBM_%d.pkl'%index
    extensions = None
    #extensions = [MonitorBasedLRAdjuster()]
    return Train(model = model, algorithm = train_algo,
                 save_path=path,save_freq=MAX_EPOCHS_UNSUPERVISED,
                 extensions = extensions, dataset = trainset)

def main():

    trainset = get_dataset_keypoints()

    trainset.apply_preprocessor(preprocessor=preprocessing.ShuffleAndSplit(seed=34533232, start=0, stop=6500), can_fit=True)
    trainset.apply_preprocessor(preprocessor=preprocessing.ZCA(filter_bias=8.0), can_fit=True)

    design_matrix = trainset.get_design_matrix()
    n_input = design_matrix.shape[1]

    # build layers
    layers = []
    structure = [[n_input, 2000], [2000, 500]]
    # layer 0: gaussianRBM
    layers.append(get_grbm(structure[0]))
    # layer 1: RBM
    layers.append(get_rbm(structure[1]))

    #construct training sets for different layers
    trainset = [ trainset ,
                TransformerDataset( raw = trainset, transformer = layers[0] )]  
    
    # construct layer trainers
    layer_trainers = []
    layer_trainers.append(get_layer_trainer_sgd_rbm(layers[0], trainset[0], 1))
    layer_trainers.append(get_layer_trainer_sgd_rbm(layers[1], trainset[1], 2))

    #unsupervised pretraining
    for i, layer_trainer in enumerate(layer_trainers[0:2]):
        print '-----------------------------------'
        print ' Unsupervised training layer %d, %s'%(i, layers[i].__class__)
        print '-----------------------------------'
        layer_trainer.main_loop()

    print '\n'
    print '------------------------------------------------------'
    print ' Unsupervised training done! Start supervised training...'
    print '------------------------------------------------------'
    print '\n'

    #supervised training
    #layer_trainers[-1].main_loop()


if __name__ == '__main__':
    main()

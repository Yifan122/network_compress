import argparse
import torch
from models.resnet import *
import torch.nn as nn
from src.data_loader import get_data_loader
from config import config
from src.train_val import train, validate
from src.TaylorExpansionPrunner import TaylerExpansionPrunner
from utils.find_zero_param import analyse_network


class PrunningFineTuner:
    def __init__(self, train_path, test_path, model, block_type):
        self.train_data_loader = get_data_loader(train_path, config.val_batch_size, config.num_workers, type='train')
        self.val_data_loader = get_data_loader(test_path, config.val_batch_size, config.num_workers, type='val')

        self.model = model
        self.block_type = block_type
        self.criterion = torch.nn.CrossEntropyLoss()
        self.pruner = TaylerExpansionPrunner(self.model, block_type)
        self.model.train()

    def train(self, baseline_model=None, attention_transfer=False, distillation_knowledge=False):
        optimizer = torch.optim.SGD(self.model.parameters(), config.lr,
                                    momentum=config.momentum)
        train(self.train_data_loader, self.model, baseline_model, self.criterion, optimizer,
              attention_transfer=attention_transfer,
              distillation_knowledge=distillation_knowledge)

    def val(self):
        validate(self.val_data_loader, self.model, self.criterion, print_fre=200, exit=config.val_exit,
                 devices_id=config.device_ids)


    def prune(self):
        self.model.train()

        # Make sure all the layers are trainable
        for param in self.model.parameters():
            param.requires_grad = True

        # Get the filter ranking
        self.pruner.calculateTaylor(self.train_data_loader, self.criterion)

        for i in range(10):
            self.pruner.get_min_taylor_filter()
            self.pruner.deleteFilter()
            analyse_network(self.model)
            print(self.pruner.filter_delete)
            print('*'*33)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", dest="train", action="store_true")
    parser.add_argument("--prune", dest="prune", action="store_true")
    parser.add_argument("--train_path", type=str, default=config.train_path)
    parser.add_argument("--test_path", type=str, default=config.val_path)
    parser.set_defaults(train=False)
    parser.set_defaults(prune=False)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = get_args()

    resnet, block_type = resnet50(pretrained=True)

    print(resnet)

    baseline_model, _ = resnet50(pretrained=True)

    # from src.deleteFilter import deleterFilterPerBlock
    # from utils.find_zero_param import analyse_network
    # deleteList = [(0, 1, 2, 3), (4, 5, 6)]
    #
    # # for index in deleteList:
    # deleterFilterPerBlock(resnet, 'layer1', 0, deleteList, block_type)
    #
    # analyse_network(resnet)
    # print('yes')

    for param in baseline_model.parameters():
        param.requires_grad = False

    fine_tuner = PrunningFineTuner(args.train_path, args.test_path, resnet, block_type)
    fine_tuner.prune()
    #
    fine_tuner.train(baseline_model=baseline_model, distillation_knowledge=True, attention_transfer=False)

    fine_tuner.val()



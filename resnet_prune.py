import argparse
import torch
import torchvision.models as models
import torch.nn as nn
from pytorch.data_loader import get_data_loader
from config import config
from pytorch.train_val import train, validate


class FilterPrunner:
    def __init__(self, model):
        self.model = model


class PrunningFineTuner:
    def __init__(self, train_path, test_path, model):
        self.train_data_loader = get_data_loader(train_path, config.val_batch_size, config.num_workers, type='train')
        self.val_data_loader = get_data_loader(test_path, config.val_batch_size, config.num_workers, type='val')

        self.model = model
        self.criterion = torch.nn.CrossEntropyLoss()
        self.prunner = FilterPrunner(self.model)
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

    resnet = models.resnet18(pretrained=True)

    baseline_model = models.resnet50(pretrained=True)

    for param in baseline_model.parameters():
        param.requires_grad = False

    fine_tuner = PrunningFineTuner(args.train_path, args.test_path, resnet)

    fine_tuner.train(baseline_model=baseline_model, distillation_knowledge=True, attention_transfer=False)

    fine_tuner.val()
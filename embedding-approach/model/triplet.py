from utils.losses import triplet_semihard_loss
import pytorch_lightning as pl
from torchmetrics import Accuracy
from torch import Tensor
from utils.dataset import IndividualsDS
from sklearn.model_selection import train_test_split#
from torch.optim import Adam
from torch.utils.data import DataLoader
from torch.nn import Linear, AdaptiveAvgPool2d
import torch
import pandas as pd
from torchvision.models import Inception_V3_Weights
from torchvision import transforms
from typing import Tuple
import numpy as np
from .inception import inception_modified as test
from .inception import InceptionOutputs
from utils.batch_sampler_triplet import TripletBatchSampler
from utils.batch_sampler_ensure_positives import BatchSamplerEnsurePositives

class TripletLoss(pl.LightningModule):
    def __init__(self, df:pd.DataFrame, embedding_size, img_size: Tuple[int, int]=[300,300], batch_size=32, lr=0.00001, ):
        super(TripletLoss, self).__init__()
        self.save_hyperparameters()
        self.df = df
        self.batch_size = batch_size
        self.lr = lr
        self.img_size = img_size
        num_classes=self.df["labels_numeric"].nunique()
        print("DGHHWG", num_classes)
        #self.valAcc = Accuracy("multiclass", num_classes=num_classes)
        #self.trainAcc = Accuracy("multiclass", num_classes=num_classes)

        #backend
        self.backend = test(weights=Inception_V3_Weights.IMAGENET1K_V1)
        self.backend.eval()
        # "frontend"
        self.pooling = AdaptiveAvgPool2d((5,5))
        self.linear = Linear(2048*5*5, embedding_size)
    
    def forward(self, x: Tensor):
        x = self.backend(x)
        if isinstance(x, InceptionOutputs):
            x = x.logits

        x = self.pooling(x)
        x = x.flatten(start_dim=1)
        x = self.linear(x)
        return x

    def prepare_data(self):
        train, validate = train_test_split(self.df, test_size=0.3, random_state=0, stratify=self.df['labels_numeric'])
        self.train_ds = IndividualsDS(train, self.img_size)
        self.validate_ds = IndividualsDS(validate, self.img_size)
        self.batch_sampler_train = BatchSamplerEnsurePositives(ds=self.train_ds, batch_size=self.batch_size)
        self.batch_sampler_val = BatchSamplerEnsurePositives(ds=self.validate_ds, batch_size=self.batch_size)

    def configure_optimizers(self):
        return Adam(self.parameters(), lr=self.lr, betas=(0.9, 0.99), eps=1e-08, weight_decay=0.0)

    def train_dataloader(self):
        # ToDo: Implement data augmentation as in the paper
        return DataLoader(self.train_ds, batch_sampler=self.batch_sampler_train, num_workers=8)

    def val_dataloader(self):
        return DataLoader(self.validate_ds, batch_sampler=self.batch_sampler_val, num_workers=8)

    def training_step(self, batch: dict, _batch_idx: int):
        inputs, labels = batch['images'], batch['labels']
        labels = labels.flatten()
        outputs = self.forward(inputs)
        loss = triplet_semihard_loss(labels, outputs, 'cuda:0')
        #self.trainAcc(outputs.argmax(dim=1), labels)
        #self.log('train_loss', loss, on_step=False, ontripe_epoch=True, prog_bar=False)
        #self.log('train_loss', loss, on_step=False, prog_bar=False)
        return loss

    def training_epoch_end(self, training_step_outputs):
        #self.log('train_acc', self.trainAcc.compute() * 100, prog_bar=True)
        #self.trainAcc.reset()
        pass

    def validation_step(self, batch: dict, _batch_idx: int):
        inputs, labels = batch['images'], batch['labels']
        #print("labels", labels)
        #print("labels", np.shape(labels))
        labels = labels.flatten()
        outputs = self.forward(inputs)

        loss = triplet_semihard_loss(labels, outputs, 'cuda:0')
        #print("loss", loss)
        #print("outputs", outputs)
        #print("outputs", np.shape(outputs))
        #print("labels", labels)
        #print("labels", np.shape(labels))
        #self.valAcc(outputs.argmax(dim=1), labels)
        
        return {'val_loss': loss}
    
    def validation_epoch_end(self, validationStepOutputs):
        avgLoss = torch.stack([x['val_loss'] for x in validationStepOutputs]).mean()
        #valAcc = self.valAcc.compute() * 100
        #self.valAcc.reset()
        self.log('val_loss', avgLoss, prog_bar=True)
        #self.log('val_acc', valAcc, prog_bar=True)

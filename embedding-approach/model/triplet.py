from utils.losses import triplet_semihard_loss
import pytorch_lightning as pl
from torch import Tensor
from utils.dataset import IndividualsDS
from sklearn.model_selection import train_test_split
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
from utils.batch_sampler_by_class import BatchSamplerByClass
from utils.dataset_utils import custom_train_val_split
from utils.data_augmentation import DataAugmentation
import wandb

class TripletLoss(pl.LightningModule):
    def __init__(self, df:pd.DataFrame, embedding_size, img_size: Tuple[int, int]=[300,300], batch_size=32, lr=0.00001,
                 sampler="class_sampler", use_augmentation=False, train_val_split_overlapping=False,
                 augment_config={"use_erase": False, "use_intensity": False, "use_geometric": True}):
        super(TripletLoss, self).__init__()
        self.save_hyperparameters()
        self.df = df
        self.batch_size = batch_size
        self.lr = lr
        self.img_size = img_size
        self.sampler = sampler
        self.use_augmentation = use_augmentation
        self.augment_batch = DataAugmentation(augment_config)
        self.train_val_split_overlapping = train_val_split_overlapping
        num_classes=self.df["labels_numeric"].nunique()
        print("Amount of individuals", num_classes)

        # backend building a feature map
        self.backend = test(weights=Inception_V3_Weights.IMAGENET1K_V1)
        self.backend.eval()
        # global average pooling over feature maps to avoid overfitting
        self.pooling = AdaptiveAvgPool2d((5,5))
        # filly connected layer to create the embedding vector
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
        print("Preparing Data...")
        if self.train_val_split_overlapping:
            train, validate = train_test_split(self.df, test_size=0.3, random_state=0, stratify=self.df['labels_numeric'])
        else:
            train, validate = custom_train_val_split(self.df, test_size=0.3, random_state=0, label_col_name="labels_numeric")
        self.train_ds = IndividualsDS(train, self.img_size)
        self.validate_ds = IndividualsDS(validate, self.img_size)
        if self.sampler == "class_sampler": 
            self.batch_sampler_train = BatchSamplerByClass(ds=self.train_ds)
            self.batch_sampler_val = BatchSamplerByClass(ds=self.validate_ds)
        elif self.sampler == "ensure_positive":
            self.batch_sampler_train = BatchSamplerEnsurePositives(ds=self.train_ds, batch_size=self.batch_size)
            self.batch_sampler_val = BatchSamplerEnsurePositives(ds=self.validate_ds, batch_size=self.batch_size)
        print("Preparing Data completed.")

    def configure_optimizers(self):
        return Adam(self.parameters(), lr=self.lr, betas=(0.9, 0.99), eps=1e-08, weight_decay=0.0)

    def train_dataloader(self):
        if self.sampler == "class_sampler":
            return DataLoader(self.train_ds, batch_sampler=self.batch_sampler_train, num_workers=16)
        elif self.sampler == "random_sampler":
            return DataLoader(self.train_ds, batch_size=self.batch_size, shuffle=True, num_workers=4, drop_last=True)
        elif self.sampler == "ensure_positive":
            return DataLoader(self.train_ds, batch_sampler=self.batch_sampler_train, num_workers=8)
        raise Exception("No sampler specified")

    def val_dataloader(self):
        if self.sampler == "class_sampler":
            return DataLoader(self.validate_ds, batch_sampler=self.batch_sampler_val, num_workers=16)
        elif self.sampler == "random_sampler":
            return DataLoader(self.validate_ds, batch_size=self.batch_size, shuffle=True, num_workers=4, drop_last=True)
        elif self.sampler == "ensure_positive":
            return DataLoader(self.train_ds, batch_sampler=self.batch_sampler_train, num_workers=8)
        raise Exception("No sampler specified")

    def on_after_batch_transfer(self, batch, dataloader_idx):
        # GPU & Batched Data augmentation being applied to training
        if self.use_augmentation and self.trainer.training:
            batch["images"] = self.augment_batch(batch["images"])
        return batch

    def training_step(self, batch: dict, _batch_idx: int):
        inputs, labels = batch['images'], batch['labels']
        labels = labels.flatten()
        outputs = self.forward(inputs)
        loss = triplet_semihard_loss(labels, outputs, 'cuda:0')
        #self.log("train/loss", loss)
        wandb.log({'train_loss': loss})
        return loss

    def training_epoch_end(self, training_step_outputs):
        pass

    def validation_step(self, batch: dict, _batch_idx: int):
        inputs, labels = batch['images'], batch['labels']
        labels = labels.flatten()
        outputs = self.forward(inputs)

        loss = triplet_semihard_loss(labels, outputs, 'cuda:0')
        self.log('val_loss', loss)
        wandb.log({'val_loss': loss})
        
        return {'val_loss': loss}
    
    def validation_epoch_end(self, validationStepOutputs):
        avgLoss = torch.stack([x['val_loss'] for x in validationStepOutputs]).mean()
        self.log('avg_val_loss_epoch', avgLoss, prog_bar=True)
        wandb.log({'avg_val_loss_epoch': avgLoss})


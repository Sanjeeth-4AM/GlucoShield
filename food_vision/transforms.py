"""
GlucoShield Food Vision Transforms
==================================
Image preprocessing and data augmentation pipelines for training and validation.
Standardizes images to 224x224 RGB with ImageNet channel normalization.
"""

import torchvision.transforms as T

def get_train_transforms(image_size: int = 224) -> T.Compose:
    """
    Stochastic training transforms with data augmentations:
      - Random resized crop
      - Random horizontal flip
      - Slight color jitter (brightness, contrast, saturation)
      - Slight random rotation (+/- 15 degrees)
      - ImageNet mean/std normalization
    """
    return T.Compose([
        T.Resize((int(image_size * 1.15), int(image_size * 1.15))),
        T.RandomCrop((image_size, image_size)),
        T.RandomHorizontalFlip(p=0.5),
        T.RandomRotation(degrees=15),
        T.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
        T.ToTensor(),
        T.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

def get_eval_transforms(image_size: int = 224) -> T.Compose:
    """
    Deterministic evaluation transforms for validation and test inference:
      - Resize to 256x256
      - Center crop to 224x224
      - ImageNet mean/std normalization
    """
    return T.Compose([
        T.Resize((int(image_size * 1.15), int(image_size * 1.15))),
        T.CenterCrop((image_size, image_size)),
        T.ToTensor(),
        T.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

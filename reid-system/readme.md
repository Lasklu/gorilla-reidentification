<h1 align="center">GorillaVision</h1>

<h2 align="center" style=font-size:200px>An open-set re-identification system for gorillas in the wild</h2>

<a name="overview"></a>
## Overview

We present a system for open-set gorilla re-identification in the wild. Our system follows a two stage approach in which gorilla faces are detected with a YOLOv7 detector in the first stage, and are classified with our GorillaVision model in the second stage. We implement our classification model based on the VisionTransformer that is optimized with Triplet Loss and that computes embeddings of gorilla faces. As in many face-identification tasks, the embeddings are then used, to provide a similarity measure between the individual gorillas. Classification is then performed on these embeddings with a k-nearest neighbors algorithm. For a closed-set scenario, our approach slightly outperforms the state-of-the art YOLO detector. In the open-set scenario, our model is also able to deliver high quality results with an accuracy in the range of 60 to 80\% depending on the quality of the dataset. Given that we have many individuals with at least 6 images each, our approach achieves 89\% top-5 accuracy.

<a name="structure"></a>
## Structure
The code for the gorillavision module is located in the reid-system/gorillavision folder. The files to run the gorillavision module or to run predictions are located in the reid-system folder. All other folder are from the <a href="https://github.com/deshwalmahesh/yolov7-deepsort-tracking">Yolov7-Deepsort Tracking</a> project. Changes to this code structure are difficult, since changing the imports of the yolov7-deepsort tracker lead to problems when importing pre-trained models.

<a name="running"></a>
## Running the Application

### Prediction

1. Build the docker image with `docker build -t gorilla_triplet .`
2. Provide all required arguments in the `predict.py` file in the main function. 
This includes a trained and serialized model for face and body detection, a trained and serialized model for the identfication, the images and videos that you want to predict on, and a database for identification.
3. Run the docker container and prediction with 

```docker run -v  /scratch1/wildlife_conservation/:/data -v /gorilla-reidentification/:/gorilla-reidentification --gpus device=0 --ipc="host" -it gorilla_triplet predict.py```

### Evaluation Pipeline
If you want to train a model based on your own data and directly evaluate it, we reccomend using the evaluation pipeline.
This requires 3 datasets: Training data, data to create a database from, and data that is used to evaluate and compute the metrics on.

1. Adapt the gorillavision/configs/config.json file: You only need to provide your datasets in the "main" section. Additionally, you can
adapt the model to your needs. The folder you pass into is require to include 3 subfolders: "train", "db_set" and "eval". If you want to evaluate multiple datasets / splits, you can provide all folders manually under `datasets`, otherwise you can also provide a single folder that contains all datasets that should be used under `datasets_folder`.
2. Start the docker-container and run the pipeline:

```
docker run -v  /home/mydatafolder/:/data -v /home/models/:/models -v /gorilla-reidentification/reid-system:/gorilla-reidentification/reid-system --gpus device=1 --ipc="host" -it gorilla_triplet python3 identification_pipeline.py
```

If you want to evaluate multiple configs in one go, you can use `-d |directory_name|` as a paramter for the `identification_pipeline` that provides the name of a directory that contains all configs.

### Training
#### Detection
Run the "train_detection.py" with the according dataset in the docker container to create a detection model.

#### Identification
You can also run training and database creation individually. To do so start the docker container, provide the required arguments in the according sections (train, predict and create_db) in the config file and run "train_identification.py" or "create_identification_db.py" in the docker container.

<a name="contributors"></a>
### Contributors ✨

<table>
  <tr>
    <td align="center"><a href="https://github.com/rohansaw"><img src="https://avatars.githubusercontent.com/u/49531442?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Rohan Sawahn</b></sub></a><br /></td>
    <td align="center"><a href="https://github.com/Lasklu"><img src="https://avatars.githubusercontent.com/u/49564344?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Lukas Laskowski</b></sub></a><br /></td>
  </tr>
</table>

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

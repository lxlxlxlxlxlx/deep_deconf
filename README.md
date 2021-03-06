# Deep Causal Reasoning for Recommender System

 The codes are associated with the following paper:
 >**Deep Causal Reasoning for Recommender System,**  
 >Anonymous Author(s),  
 >Submitted as a conference paper to NeurIPS 2021.


## Environment

 The codes are written in Python 3.6.5.  

- numpy == 1.16.3
- pandas == 0.21.0
- tensorflow-gpu == 1.15.0
- tensorflow-probability == 0.8.0

## Dataset Acquirement and Simulation

- **Acquire the movielens-1m and amazon-vg datasets:**  
    The pre-processed datasets can be found [[here]]().  
 Unzip the file and put them under data_sim/raw folder.

- **Preprocess the original dataset:**
    cd to data_sim/raw folder, run   
    ```python prepare_data.py --dataset Name --simulate {exposure, ratings}```.

- **Fit the exposure and rating distribution via VAEs:**
    cd to data_sim folder, run   
    ```python train.py --dataset Name --simulate {exposure, ratings}```. 

- **Simulate the causal dataset under various confounding levels:**
    ```python simulate.py --dataset Name --simulate {exposure, ratings}```. 

- **The simulated datasets are in casl/data folder**

## Fitting the exposure and rating models
- **Split the simulated causal datasets into train/val/test:**  
    cd to casl_rec/data folder, run   
    ```python preprocess.py --dataset Name --split 5```.

- **Train the exposure model, conduct predictive check:**  
    ```python train_exposure.py --dataset Name --split [0-4]```

- **Infer the subsititute confounders:**   
    ```python infer_subs_conf.py --dataset Name --split [0-4]```

- **Train the potential rating prediction model:**   
    ```python train_ratings.py --dataset Name --split [0-4]```

- **Predict the scores for hold-out users:**   
    ```python evaluate_model.py --dataset Name --split [0-4]```

**For advanced argument usage, run the code with --help argument.**
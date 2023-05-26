import db

import numpy as np
import pandas as pd

import catboost as cb
from lightautoml.automl.presets.tabular_presets import TabularUtilizedAutoML
from lightautoml.tasks import Task
import torch
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from datetime import datetime
from sklearn.metrics import mean_squared_error
import optuna
import pickle
import os


def prepoc(df):
    df = df[df['date'].notna()]
    df = df[df['sum'].notna()]
    #df = df[df['type'].notna()]
    df['date'] = pd.to_datetime(df['date'])
    df_sum = df.copy()
    last = ''
    for i, row in df.iterrows():
        if row['date'] != last:
            df_sum.loc[(df_sum['date'] == row['date']), 'sum'] = sum(df[df['date'] == row['date']]['sum'])
            last = row['date']
    return df_sum


def prepoc_new(df):
    df['date'] = pd.to_datetime(df['date'], unit='s')
    # если данные с временем
    for i in range(len(df)):
        df['date'][i] = df['date'][i].date()
    df['date'] = pd.to_datetime(df['date'])
    return df


def make_features(df):
    df['day'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] > 4).astype('int16')

    df['is_winter'] = ((df['month'] >= 12) & (df['month'] <= 2)).astype('int16')
    df['is_spring'] = ((df['month'] > 2) & (df['month'] <= 5)).astype('int16')
    df['is_summer'] = ((df['month'] > 5) & (df['month'] <= 8)).astype('int16')
    df['is_autumn'] = ((df['month'] > 8) & (df['month'] <= 11)).astype('int16')

    '''funcs,nms = get_funcs()
    for i, func in enumerate(funcs):
        for col in ['day', 'month']:
            df[f"{nms[i]}_func_{col}"] = func(df[col])'''
    # return df.drop(columns=['date'])
    return df


SAMPLE_RATE = 0.4
RANDOM_SEED = 1
EARLY_STOPPING_ROUND = 100
# выделим категориальные фичи для катбуста
CAT_COLUMNS = ['day', 'month', 'day_of_week', 'is_weekend', 'is_winter', 'is_spring', 'is_summer', 'is_autumn']


def catboost(df, new_df):
    ft = prepoc(df)
    X_train, X_valid, y_train, y_valid = train_test_split(ft[['date']], ft['sum'], test_size=0.2,
                                                              shuffle=False)
    X_train, X_eval, y_train, y_eval = train_test_split(X_train, y_train, test_size=0.1, shuffle=False)
    X_train = make_features(X_train)
    # X_train = X_train.drop(columns=['date'])
    X_eval = make_features(X_eval)
    X_valid = make_features(X_valid)
    # X_eval = X_eval.drop(columns=['date'])

    def objective(trial):
        param = {}
        param['learning_rate'] = trial.suggest_discrete_uniform("learning_rate", 0.001, 0.02, 0.001)
        param['depth'] = trial.suggest_int('depth', 9, 15)
        param['l2_leaf_reg'] = trial.suggest_discrete_uniform('l2_leaf_reg', 1.0, 5.5, 0.5)
        param['min_child_samples'] = trial.suggest_categorical('min_child_samples', [1, 4, 8, 16, 32])
        param['grow_policy'] = 'Depthwise'
        param['iterations'] = 100
        param['use_best_model'] = True
        param['eval_metric'] = 'RMSE'
        param['od_type'] = 'iter'
        param['od_wait'] = 20
        param['random_state'] = RANDOM_SEED
        param['logging_level'] = 'Silent'

        regressor = cb.CatBoostRegressor(**param)

        regressor.fit(X_train.copy().drop(columns=['date']), y_train.copy(),
                      eval_set=[(X_eval.copy().drop(columns=['date']), y_eval.copy())],
                      early_stopping_rounds=EARLY_STOPPING_ROUND)
        loss = mean_squared_error(y_valid, regressor.predict(X_valid.copy()))
        return loss
    study = optuna.create_study(study_name=f'catboost-seed{RANDOM_SEED}')
    study.optimize(objective, n_trials=100, n_jobs=-1, timeout=24000, show_progress_bar=True)

    optimized_regressor = cb.CatBoostRegressor(learning_rate=study.best_params['learning_rate'],
                                            depth=study.best_params['depth'],
                                            l2_leaf_reg=study.best_params['l2_leaf_reg'],
                                            min_child_samples=study.best_params['min_child_samples'],
                                            grow_policy='Depthwise',
                                            iterations=100,
                                            use_best_model=True,
                                            eval_metric='RMSE',
                                            od_type='iter',
                                            od_wait=20,
                                            random_state=RANDOM_SEED,
                                            logging_level='Silent',
                                           cat_features=CAT_COLUMNS)
    optimized_regressor.fit(X_train.copy().drop(columns=['date']), y_train.copy(),
                            eval_set=[(X_eval.copy().drop(columns=['date']), y_eval.copy())],
                            early_stopping_rounds=EARLY_STOPPING_ROUND)
    new_df = make_features(prepoc_new(new_df))
    res = dict()
    res['date'] = new_df['date']
    res['sum'] = optimized_regressor.predict(new_df.drop(columns=['date']))
    #pred_train = optimized_regressor.predict(X_train.copy().drop(columns=['date']))
    #pred_valid = optimized_regressor.predict(X_valid.copy().drop(columns=['date']))
    '''Path(f'files/{user_id}/models').mkdir(parents=True, exist_ok=True)
    with open(f"files/{user_id}/models/model_catboost.pkl", 'wb') as f:
        pickle.dump(optimized_regressor, f)'''

    return pd.DataFrame(res)


def catboost_predict(df, user_id):
    model_dir = f"files/{user_id}/models"
    df = prepoc_new(df)
    res = dict()
    res['date'] = df['date']
    targets = os.listdir(model_dir)
    good_df = make_features(df.copy())
    for target in targets:
        if target == 'model_catboost.pkl':
            model = [pickle.load(open(f"{model_dir}/{target}", 'rb'))][0]
            preds = model.predict(good_df.drop(columns=['date']))
            # models = [pickle.load(open(f"{model_dir}/{target}", 'rb'))]
            # preds = np.mean([model.predict(good_df) for model in models], axis=0)
            res[target] = preds
    return pd.DataFrame(res)


# параметры для lama
N_THREADS = 40
N_FOLDS = 3
RANDOM_STATE = 56
TEST_SIZE = 0.2
TIMEOUT = 10


np.random.seed(RANDOM_STATE)
torch.set_num_threads(N_THREADS)

task = Task('reg')


def lama(df, new_df):
    train = prepoc(df)
    train = make_features(train)

    TARGET_NAME = 'sum'
    roles = {
        'target': TARGET_NAME,
    }
    automl = TabularUtilizedAutoML(
        task=task,
        timeout=TIMEOUT,
        cpu_limit=N_THREADS,
        reader_params={'n_jobs': N_THREADS, 'cv': N_FOLDS, 'random_state': RANDOM_STATE})
    oof_pred = automl.fit_predict(train, roles=roles, verbose=False)
    new_df = make_features(prepoc_new(new_df))
    res = automl.predict(new_df)
    df = pd.DataFrame(res.data[:, 0], columns=['sum'])
    df['date'] = new_df['date']
    return df


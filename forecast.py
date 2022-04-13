import numpy as np
import tensorflow as tf
import pandas as pd

from tensorflow import keras
from datetime import datetime

def get_scaled(df, scaler, time_steps):
    df_scaled = scaler.transform(np.array(df.tail(time_steps)).reshape(-1, 1))
    return df_scaled
    
def get_inverse(pred_values, scaler):
    df_inverse = scaler.inverse_transform(pred_values.reshape(-1,1)).reshape(-1)
    return np.round(df_inverse, decimals=0)

def read_file(path):
    file = pd.read_csv(path, parse_dates=['date'], index_col='date')
    file = file.sort_values(by='date', ascending=True)
    file = file[-30:]
    return file

def check_dates(file):
    bool = file['date'].max().to_pydatetime() <= datetime.now()
    print(bool)
    return bool

def validate_file(df):
    dates = pd.date_range(start=df['date'].min(), end=df['date'].max())
    df['x'] = dates
    if dates.shape[0] != df.shape[0]:
        return False
    elif np.where(df["date"] != df["x"], True, False).all():
        return False
    elif df['date'].max().to_pydatetime() > datetime.now():
        return False
    else:
        return True
def process_json_data(dates, cases):

    cases_df = pd.DataFrame({'date':dates,'cases':cases})
    cases_df['date'] = pd.to_datetime(cases_df['date'])
    cases_df.set_index('date', inplace=True)
    return cases_df

def forecast(df, days_ahead, model, time_steps, scaler):
    pred_values = []
    df_scaled = get_scaled(df, scaler, time_steps).reshape(1, time_steps, 1)
    for _ in range(days_ahead):
        pred = model.predict(df_scaled)
        pred_values.append(max(0, pred[0][0]))
        df_scaled = np.append(df_scaled, pred.reshape(1, 1, 1), axis=1)
        df_scaled = df_scaled[:, 1 :]
    pred_values = np.array(pred_values)
    return pred_values

def predict_dates(df, days_ahead, dates):
    last_date = len(df.index)-1
    last_date = df.index[last_date]
    if dates is None:
        csv_pred_dates = pd.date_range(last_date, periods=days_ahead+1).tolist()
        return csv_pred_dates
    else:
        json_latest_date = datetime.strptime(dates[0], '%Y-%m-%dT%H:%M:%S.%fZ').date()
        json_pred_dates = pd.date_range(json_latest_date, periods=days_ahead+1).tolist()
        return json_pred_dates
    
def get_result(df, pred_values, days_ahead, scaler, dates):
    pred_cases = get_inverse(pred_values, scaler)
    
    pred_cases = np.insert(pred_cases, 0, np.array(df.tail(1)['cases']), axis=0)

    if dates is None:
        pred_dates = predict_dates(df, days_ahead, dates=None)
    else:
        pred_dates = predict_dates(df, days_ahead, dates)

    dates_list = [t.strftime("%Y-%m-%d") for t in pred_dates]

    forecasted_cases = np.asarray(pred_cases, dtype=np.int64)
    forecasted_cases = forecasted_cases.tolist() 
    forecasted_tuple = [(dates_list[i], forecasted_cases[i]) for i in range(1, len(dates_list))]
    return forecasted_tuple

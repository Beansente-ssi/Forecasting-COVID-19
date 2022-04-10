import os.path, secrets, pickle, forecast, requests, json
import tensorflow as tf
from flask import Flask, render_template, request, redirect, flash, session
import pandas as pd
import numpy as np

app = Flask(__name__)

def load():
    model = tf.keras.models.load_model('model/uni_model.h5')
    scaler = pickle.load(open('model/scaler.pkl','rb'))

    return model, scaler

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "GET":    
        future_url = 'https://covid-19-albay.herokuapp.com/api/history/30'
        past_url = 'https://covid-19-albay.herokuapp.com/api/history/0'

        future = requests.get(future_url)
        past = requests.get(past_url)
        days_ahead = 14
        time_steps = 30
        model, scaler = load()

        loaded_future_data = json.loads(future.text)['cases']
        future_dates = list(loaded_future_data.keys())
        future_cases = list(loaded_future_data.values())
        future_data = forecast.process_json_data(future_dates, future_cases)

        loaded_past_data = json.loads(past.text)
        cases = list(loaded_past_data['cases'].values())
        dates = list(loaded_past_data['cases'].keys())
        sma = list(loaded_past_data['SMA_7'].values())
        ctr = dates.index('2022-01-01T00:00:00.000Z')

        dates = dates[ctr:]
        cases = cases[ctr:]
        sma = sma[ctr:]
        for i in range(len(dates)): dates[i] = dates[i].replace("T00:00:00.000Z", "")

        df = pd.DataFrame({ 
         "date": loaded_past_data['cases'].keys(),
        "cases": loaded_past_data['cases'].values(),
        "SMA_7": loaded_past_data['SMA_7'].values(),
        }).set_index("date")
        df = df.loc["2021-12-02": ]
        df_ = pd.DataFrame(scaler.fit_transform(df[['cases']]))

        data = []
        for i in range(len(df_) - 30):
            x = df_[0][i: i+30].values
            data.append(x)

        data = np.array(data)
        data = data.reshape(-1, 30, 1)
        preds = model.predict(data)
        preds_inv = forecast.get_inverse(preds, scaler)
        preds = [pred for pred in preds_inv] 
        future_pred_values = forecast.forecast(future_data, days_ahead, model, time_steps, scaler)
        future_forecasted_tuple = forecast.get_result(future_data, future_pred_values, days_ahead, scaler, dates=None)
        future_labels = [row[0] for row in future_forecasted_tuple]
        future_values = [row[1] for row in future_forecasted_tuple]

        labels = dates + future_labels
        values = preds + future_values
        return render_template("index.html", labels=labels, values=values, recorded_cases=cases, sma=sma)

@app.route("/overview-statistics")
def overview_statistics():
    return render_template("overview.html")

@app.route("/calculate-forecast")
def calculate():
    return render_template("calculate.html")

@app.route("/forecast-calculation-result", methods=["POST", "GET"])
def get_result():
    if request.method == "POST":
        try:
            uploaded_file = request.files['file']
            basepath = os.path.dirname(__file__)
            path = os.path.join(basepath, "user-uploads", uploaded_file.filename)
            file = uploaded_file.save(path)
            file = forecast.read_file(path)
            days_ahead = 14
            time_steps = 30
            model, scaler = load()

            pred_values = forecast.forecast(file, days_ahead, model, time_steps, scaler)
            forecasted_tuple = forecast.get_result(file, pred_values, days_ahead, scaler, dates=None)

            labels = [row[0] for row in forecasted_tuple]
            values = [row[1] for row in forecasted_tuple]
            return render_template("forecast-calculation.html", labels=labels, values=values)
        except (ValueError, KeyError, TypeError):
            flash("Uh oh! It looks like the file you uploaded contains more columns than necessary. Please make sure that your file follows the format.")
            return redirect('/calculate-forecast')
            
secret = secrets.token_urlsafe(32)
app.secret_key = secret

if __name__ == "__main__":
    app.run(debug=True, threaded=True)

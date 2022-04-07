import os.path, secrets, pickle, forecast, requests, json
import tensorflow as tf
from flask import Flask, render_template, request, redirect, flash, session

app = Flask(__name__)

def load():
    model = tf.keras.models.load_model('uni_model.h5')
    scaler = pickle.load(open('scaler.pkl','rb'))

    return model, scaler

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "GET":    
        url = 'https://covid-19-albay.herokuapp.com/api/history/30'
        x = requests.get(url)
        days_ahead = 13
        time_steps = 30
        model, scaler = load()

        loaded_albay_data = json.loads(x.text)['cases']
        dates = list(loaded_albay_data.keys())
        cases = list(loaded_albay_data.values())
        data = forecast.process_json_data(dates, cases)
        
        pred_values = forecast.forecast(data, days_ahead, model, time_steps, scaler)
        forecasted_tuple = forecast.get_result(data, pred_values, days_ahead, scaler, dates)

        labels = [row[0] for row in forecasted_tuple]
        values = [row[1] for row in forecasted_tuple]
        return render_template("index.html", labels=labels, values=values)

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
            days_ahead = 13
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

from flask import Flask, render_template, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.io as pio
import pytz
from configparser import ConfigParser

app = Flask(__name__)

# Load configuration file
config = ConfigParser()
config.read('config.ini')

def create_chart(source, from_date=None, to_date=None, keyword='Bitcoin'):
    client = MongoClient(config.get('Web_Charts', 'MongoClient'))
    db = client.Cluster0
    collection = db.Sentiment_Averages

    query = {"source": source, "keyword": keyword}
    if from_date and to_date:
        from_date_utc = datetime.strptime(from_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
        to_date_utc = datetime.strptime(to_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
        query['timestamp'] = {'$gte': from_date_utc, '$lte': to_date_utc}

    documents = collection.find(query)

    df = pd.DataFrame(list(documents))
    if df.empty:
        return '<p>No data available for the selected date range.</p>'

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['price'], name='Price'), secondary_y=False)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['textblob_sentiment'], name='TextBlob Sentiment'), secondary_y=True)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['vader_sentiment'], name='VADER Sentiment'), secondary_y=True)

    fig.update_xaxes(title_text="Timestamp")
    fig.update_yaxes(title_text="<b>Primary</b> Price", secondary_y=False)
    fig.update_yaxes(title_text="<b>Secondary</b> Sentiment Score", secondary_y=True)

    return pio.to_html(fig, full_html=False)

def create_chart_all_sources(from_date=None, to_date=None, keyword='Bitcoin'):
    client = MongoClient(config.get('Web_Charts', 'MongoClient'))
    db = client.Cluster0
    collection = db.Sentiment_Averages

    query = {"keyword": keyword}
    if from_date and to_date:
        from_date_utc = datetime.strptime(from_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
        to_date_utc = datetime.strptime(to_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
        query['timestamp'] = {'$gte': from_date_utc, '$lte': to_date_utc}

    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "avg_price": {"$avg": "$price"},
            "avg_textblob_sentiment": {"$avg": "$textblob_sentiment"},
            "avg_vader_sentiment": {"$avg": "$vader_sentiment"}
        }},
        {"$sort": {"_id": 1}}
    ]
    aggregated_data = collection.aggregate(pipeline)

    df = pd.DataFrame(list(aggregated_data))

    if df.empty:
        return '<p>No data available for the selected date range.</p>'

    df['_id'] = pd.to_datetime(df['_id'])

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df['_id'], y=df['avg_price'], name='Average Price'), secondary_y=False)
    fig.add_trace(go.Scatter(x=df['_id'], y=df['avg_textblob_sentiment'], name='Average TextBlob Sentiment'), secondary_y=True)
    fig.add_trace(go.Scatter(x=df['_id'], y=df['avg_vader_sentiment'], name='Average VADER Sentiment'), secondary_y=True)

    return pio.to_html(fig, full_html=False)

@app.route('/', methods=['GET'])
def charts():
    default_to_date = datetime.now() + timedelta(days=1)
    default_from_date = default_to_date - timedelta(days=30)

    default_from_date_str = default_from_date.strftime('%Y-%m-%d')
    default_to_date_str = default_to_date.strftime('%Y-%m-%d')

    from_date = request.args.get('from_date', default_from_date_str)
    to_date = request.args.get('to_date', default_to_date_str)
    keyword = request.args.get('keyword', 'Bitcoin')

    graph_html_all_sources = create_chart_all_sources(from_date, to_date, keyword)
    graph_html_reddit = create_chart("Reddit", from_date, to_date, keyword)
    graph_html_mastodon = create_chart("Mastodon", from_date, to_date, keyword)
    graph_html_newsappi = create_chart("NewsApi", from_date, to_date, keyword)

    return render_template('chart.html', 
                           graph_html_all_sources=graph_html_all_sources,
                           graph_html_reddit=graph_html_reddit,
                           graph_html_mastodon=graph_html_mastodon,
                           graph_html_newsapi=graph_html_newsappi, 
                           from_date=from_date, 
                           to_date=to_date,
                           keyword=keyword)

if __name__ == '__main__':
    app.run(debug=True)

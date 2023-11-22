from flask import Flask, render_template, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.io as pio
import pytz

app = Flask(__name__)

def create_chart(source, from_date=None, to_date=None):
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017')
    db = client.SocialMedia_Analysis
    collection = db.Sentiment_Averages

    # Prepare query with date filters
    query = {"source": source}
    if from_date and to_date:
        from_date_utc = datetime.strptime(from_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
        to_date_utc = datetime.strptime(to_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
        query['timestamp'] = {'$gte': from_date_utc, '$lte': to_date_utc}

    documents = collection.find(query)

    # Create a DataFrame and handle empty DataFrame
    df = pd.DataFrame(list(documents))
    if df.empty:
        return '<p>No data available for the selected date range.</p>'

    # Convert 'timestamp' to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Create a subplot with two y-axes
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add Bitcoin price plot
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['price'], name='Bitcoin Price'),
        secondary_y=False,
    )

    # Add TextBlob sentiment plot
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['textblob_sentiment'], name='TextBlob Sentiment'),
        secondary_y=True,
    )

    # Add VADER sentiment plot on the same axis as TextBlob
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['vader_sentiment'], name='VADER Sentiment'),
        secondary_y=True,
    )

    # Set x-axis title
    fig.update_xaxes(title_text="Timestamp")

    # Set y-axes titles
    fig.update_yaxes(title_text="<b>Primary</b> Bitcoin Price", secondary_y=False)
    fig.update_yaxes(title_text="<b>Secondary</b> Sentiment Score", secondary_y=True)

    # Convert plot to HTML string
    return pio.to_html(fig, full_html=False)

@app.route('/', methods=['GET'])
def charts():
    # Default 'to_date' is tomorrow at the end of the day
    default_to_date = datetime.now() + timedelta(days=1)
    default_from_date = default_to_date - timedelta(days=30)

    # Format the dates as strings
    default_from_date_str = default_from_date.strftime('%Y-%m-%d')
    default_to_date_str = default_to_date.strftime('%Y-%m-%d')

    # Get the dates from the request, or use the defaults
    from_date = request.args.get('from_date', default_from_date_str)
    to_date = request.args.get('to_date', default_to_date_str)

    graph_html_mastodon = create_chart("Mastodon", from_date, to_date)
    graph_html_reddit = create_chart("Reddit", from_date, to_date)
    
    return render_template('chart.html', 
                           graph_html_mastodon=graph_html_mastodon, 
                           graph_html_reddit=graph_html_reddit,
                           from_date=from_date, 
                           to_date=to_date)

if __name__ == '__main__':
    app.run(debug=True)

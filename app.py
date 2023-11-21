from flask import Flask, render_template
from pymongo import MongoClient
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.io as pio 

app = Flask(__name__)

def create_chart(source):
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017')
    db = client.SocialMedia_Analysis
    collection = db.Sentiment_Averages

    # Query the database for the given source
    query = {"source": source}
    documents = collection.find(query)

    # Create a DataFrame
    df = pd.DataFrame(list(documents))

    # Ensure timestamp is a datetime object for proper plotting
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

@app.route('/')
def charts():
    # Create charts for Mastodon and Reddit
    graph_html_mastodon = create_chart("Mastodon")
    graph_html_reddit = create_chart("Reddit")

    return render_template('chart.html',
                           graph_html_mastodon=graph_html_mastodon,
                           graph_html_reddit=graph_html_reddit)

if __name__ == '__main__':
    app.run(debug=True)
# MkRk: News reporting & sentiment analysis

News scraping web app with sentiment analysis - concept exercise
 
## Tech stack overview

- Python 3.6 with the following main libraries
    - Django 2.1  
    - Django Rest Framework 3.9
    - Celery 4.2
    - Pandas
    - NewsAPI API client wrapper (newsapi)
    - IBM NLU API client wrapper (watson-developer-cloud)
    
- PostgreSQL database (for the native support of the JSONField)
- a message broker for Celery (e.g. RabbitMQ)

## Prerequisites

#### NewsAPI API key

To fetch the news articles we use NewsAPI service. An API key can be requested for free here:
https://newsapi.org/  

#### IBM Cloud API Key

For the article sentiment analysis we use the Natural Language Understanding service on IBM Cloud.
There a free tier as well upon registration for IBM Cloud.
The documentation is available here: https://cloud.ibm.com/apidocs/natural-language-understanding


## Setup

Steps needed to get it up and running locally:

1. Prepare the virtual environment and install the modules:
```
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

2. Edit the local.env to your use and then setup the db schemas: 
```
source local.env
./manage.py makemigrations main
./manage.py migrate
```

3. Create a super user
```
./manage.py createsuperuser
```

4. Run the server on port 8000
```
./manage.py runserver 8000
```

5. Run the celery worker and beat
```
celery worker -A mkrk -B -E
```

## Usage

Go to `http://localhost:8000` and login using the newly created user credentials.
Navigate to the **Settings** page (`http://localhost:8000/dashboard/settings`) using the header navigation bar and add a new 'target keyword'.
Now return to the **News** page (`http://localhost:8000/dashboard/news`) and you should see it populated with the latest news articles containing that keyword.
Moreover a sentiment analysis will show what are the keywords associated with each article and their 
positive/neutral or negative sentiment.
In the **Trends** page (`http://localhost:8000/dashboard/trends`) the daily average sentiment score of each target keyword is drawn.

## Under the hood

All the target keywords get periodically checked by a celery worker and new articles are fetched and analysed.
Whenever a user adds a new target an historic query for that keyword is performed on the articles of the last 30 days.

The web app can already serve content via API using the Django Rest Framework. An example of which is used
in the **Settings** page to add/delete target keywords via AJAX.
For example check out: `http://localhost:8000/api/v1/article`

The Django admin is also enabled: `http://localhost:8000/admin`


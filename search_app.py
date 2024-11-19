from flask import Flask, request
from markupsafe import escape
from flask import render_template
from elasticsearch import Elasticsearch
import math

# Change pasword
ELASTIC_PASSWORD = "p12341234"
es = Elasticsearch("https://localhost:9200", http_auth=("elastic", ELASTIC_PASSWORD), verify_certs=False)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    page_size = 9  
    keyword = request.args.get('keyword', '').strip()
    page_no = int(request.args.get('page', 1)) 
    
    try:
        keyword = float(keyword)
        isnum = True
    except ValueError:
        isnum = False

    # Split the keyword into words
    keywords = keyword.split()

    # Create query body
    if isnum:  # Numeric search
        body = {
            'query': {
                'bool': {
                    'should': [
                        {
                            'multi_match': {
                                'query': keyword,
                                'fields': ['Goals', 'Assists', 'Appearances', 'Yellow cards', 'Red cards'],
                                'operator': 'or'
                            }
                        }
                    ]
                }
            },
            'from': (page_no - 1) * page_size, 
            'size': page_size 
        }
    else:  # Textual search
        body = {
            'query': {
                'bool': {
                    'should': [
                        # Fuzzy multi-match
                        {
                            'multi_match': {
                                'query': keyword,
                                'fields': ['Name', 'Club', 'Nationality', 'Position'],
                                'fuzziness': 'AUTO',  # Enable fuzziness
                                'operator': 'or'
                            }
                        },
                        # Exact phrase match (no fuzziness)
                        {
                            'match_phrase': {
                                'Name': keyword
                            }
                        },
                        # Query string with wildcards and fuzziness
                        {
                            'query_string': {
                                'query': ' '.join([f"*{escape(word)}*" for word in keywords]),
                                'fields': ['Name', 'Club', 'Nationality', 'Position'],
                                'default_operator': 'or'
                            }
                        }
                    ]
                }
            },
            'from': (page_no - 1) * page_size,  
            'size': page_size  
        }

    # Query Elasticsearch
    res = es.search(index='premier_league_football_player', body=body)

    # Map hits to display fields
    hits = [{
        'Name': doc['_source']['Name'],
        'Club': doc['_source']['Club'],
        'Nationality': doc['_source']['Nationality'],
        'Position': doc['_source']['Position'],
        'Goals': doc['_source']['Goals'],
        'Assists': doc['_source']['Assists'],
        'Appearances': doc['_source']['Appearances'],
        'Yellow cards': doc['_source']['Yellow cards'],
        'Red cards': doc['_source']['Red cards'],
        'Image': doc['_source'].get('Image', 'default_image_url_here'), 
        'Score': doc['_score']
    } for doc in res['hits']['hits']]

    # Calculate total pages
    total_hits = res['hits']['total']['value']
    page_total = math.ceil(total_hits / page_size)

    return render_template('search.html', keyword=keyword, hits=hits, page_no=page_no, page_total=page_total)



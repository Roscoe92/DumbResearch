from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scrape_logic.scrape import (
    scrape_website,
    split_dom_content,
    clean_body_content,
    extract_body_content,
    get_all_links,
    extract_second_level_headlines,
    re_match_second_level_headlines,
    get_select_data
)

app = FastAPI()

# Allowing all middleware is optional, but good practice for dev purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Define a root `/` endpoint
@app.get('/')
def index():
    return {'ok': True}

@app.get("/parse")
def parse(domain):
    links = get_all_links(domain)
    return links

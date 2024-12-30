from scraper.link_utils import preprocess
from processing import scrape_to_df

def run_research(website, parse_description):
    # `website` is either a single URL or a list of URLs
    links, content = preprocess(website)
    output = scrape_to_df(content, parse_description)
    return output

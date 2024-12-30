# cli/user_interaction.py

import re
import pandas as pd
from scraper.link_utils import choose_links, get_all_links

def is_valid_url(url):
    parsed = re.compile(r'^(https?:\/\/)?([\w.-]+)+(:\d+)?(\/[\w._-]*)*\/?$')
    return parsed.match(url)

def select_topics():
    website_input = input("\nPlease paste the websites you'd like to explore, separated by commas: ")
    if not website_input.strip():
        print("No websites entered. Please try again.")
        return []

    websites = [str(x.strip().lower().rstrip("/")) for x in website_input.split(",") if x.strip()]
    valid_websites = [x for x in websites if is_valid_url(x)]
    if len(valid_websites) == 0:
        print("No valid websites provided.")
        return []
    print(f"Websites selected: {', '.join(valid_websites)}")
    return valid_websites

def user_selects(players=None):
    if players is None:
        domains = select_topics()
    else:
        if isinstance(players, pd.Series):
            domains = players.tolist()
        else:
            domains = players
    domain_links = {}
    for domain in domains:
        initial_links, initial_content = get_all_links(domain)
        domain_links[domain] = choose_links(initial_links)
    return domain_links

def user_task():
    user_input = input('\nPlease let DumbResearch know:\n1. What web content it is looking at\n2. What columns you would like your research output table to have.\n')
    return user_input


def initialize_dumbresearch(players = None):
    if players is not None and not isinstance(players, (list, pd.Series)):
        raise ValueError("`players` must be a list or Pandas Series of URLs")
    domains_selected = user_selects(players)
    return domains_selected

def dumbresearch_workflow(players = None):
    from scraper.link_utils import preprocess
    from processing.extraction import scrape_to_df

    domains = initialize_dumbresearch(players)
    outputs = {}
    for key in domains.keys():
        links, content = preprocess(domains[key])
        output = scrape_to_df(content)
        outputs[key] = output
    return outputs

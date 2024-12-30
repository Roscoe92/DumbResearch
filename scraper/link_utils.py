import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from .scraper import run_selenium

def extract_body_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""

def clean_body_content(body_content):
    soup = BeautifulSoup(body_content, 'html.parser')
    for script_or_style in soup(['script', 'style']):
        script_or_style.extract()
    cleaned_content = soup.get_text(separator='\n')
    cleaned_content = '\n'.join(
        line.strip() for line in cleaned_content.splitlines() if line.strip()
    )
    return cleaned_content

def get_all_links(domain):
    links_to_visit = []
    cleaned_content = ""
    try:
        html = run_selenium(domain)
        if html is None:
            print(f"Error: No HTML returned from run_selenium for '{domain}'")
            return links_to_visit, cleaned_content

        body_content = extract_body_content(html)
        cleaned_content = clean_body_content(body_content)

        soup = BeautifulSoup(html, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            full_url = urljoin(domain, a_tag['href'])
            links_to_visit.append(full_url)
    except Exception as e:
        print(f"Error visiting domain '{domain}': {e}")

    return links_to_visit, cleaned_content

def filter_urls_by_stem(stem_url, url_list):
    matches = []
    for random_url in url_list:
        if random_url.startswith(stem_url) and random_url not in matches and random_url != stem_url:
            matches.append(random_url)
    return matches

def process_link(link, depth=5):
    sub_links, sub_content = get_all_links(link)
    content_dict_sub = {}
    content_dict_sub[link] = sub_content

    link_set = set()
    first_pass = filter_urls_by_stem(link, sub_links)
    link_set.update(first_pass)

    frontier = set(first_pass)
    for depth_level in range(depth):
        next_frontier = set()
        for current_link in frontier:
            current_links, current_content = get_all_links(current_link)
            content_dict_sub[current_link] = current_content
            new_links = set(filter_urls_by_stem(current_link, current_links))
            new_links -= link_set
            link_set.update(new_links)
            next_frontier.update(new_links)
        frontier = next_frontier

    return (link, link_set, content_dict_sub)

def preprocess(chosen_links, depth=5):
    start_time = time.time()
    link_library = {}
    content_dict_master = {}

    max_workers = min(8, len(chosen_links))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_link = {
            executor.submit(process_link, link, depth): link
            for link in chosen_links
        }
        for future in as_completed(future_to_link):
            link = future_to_link[future]
            try:
                processed_link, link_set, content_dict_sub = future.result()
                link_library[processed_link] = list(link_set)
                content_dict_master[processed_link] = content_dict_sub
            except Exception as e:
                print(f"Error processing link {link}: {e}")

    end_time = time.time()
    print(f"\nPreprocess finished in {end_time - start_time:.2f} seconds")
    return link_library, content_dict_master

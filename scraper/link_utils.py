import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from .scraper import run_selenium

language_codes = [
    "en", "de", "fr", "es", "it", "pt", "nl", "ru", "zh", "ja", "ko", "ar", "hi", "bn", "ur", "id", "ms",
    "vi", "th", "pl", "tr", "sv", "no", "fi", "da", "cs", "hu", "ro", "el", "he", "sk", "bg", "uk", "sr",
    "hr", "sl", "lt", "lv", "et", "fa", "tl", "sw", "mt", "is", "ga", "cy", "sq", "mk"
]

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

def get_content_only(domain):
    try:
        html = run_selenium(domain)

        # If run_selenium returned None, bail out early:
        if html is None:
            print(f"Error: No HTML returned from run_selenium for '{domain}'")
            pass

        # save content
        body_content = extract_body_content(html)  # Extract body content
        cleaned_content = clean_body_content(body_content)  # Clean the content

    except Exception as e:
        # Refer to the domain (which is always defined), not full_url
        print(f"Error visiting domain '{domain}': {e}")

    return cleaned_content

def filter_urls_by_stem(base_url, candidate_urls, max_depth=0):
    """
    Filters `candidate_urls` such that:
      1) They share the same domain as `base_url`.
      2) Their path depth does not exceed `base_depth + max_depth`.
      3) They are not exactly the base URL.

    :param base_url: The main starting URL (string).
    :param candidate_urls: A list of URLs discovered from the current page.
    :param max_depth: The maximum additional path segments allowed beyond the base URL’s depth.
    :return: A list of filtered URLs.
    """
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    # Remove leading/trailing slashes to avoid empty last segment
    base_path = parsed_base.path.strip("/")
    full_base_url = f'{base_domain}/{base_path}'
    base_depth = len(full_base_url.split("/")) if full_base_url else 0

    matches = []
    for url in candidate_urls:
        parsed = urlparse(url)
        if parsed.fragment:
            continue
        candidate_base = parsed.netloc
        candidate_path = parsed.path.strip("/")
        full_candidate_url = f'{candidate_base}/{candidate_path}'
        candidate_depth = len(full_candidate_url.split("/")) if full_candidate_url else 0
        # 1) Ensure same domain + that candidate url is a level down from base url
        if full_candidate_url.split('/')[:base_depth] == full_base_url.split("/") and candidate_depth > base_depth:
            if candidate_depth - base_depth <= (max_depth + 1):
                matches.append(url)

    return matches

def process_link(link, base_url, depth=0):
    """
    Processes a single link by:
      1) Getting sub_links and content
      2) Filtering based on the original base_url + max_depth
      3) Expanding up to 'depth' levels
      4) Returning (link, link_set, content_dict_sub)
    """
    # 1) Grab links & content for this page
    sub_links, sub_content = get_all_links(link)

    content_dict_sub = {}
    content_dict_sub[link] = sub_content

    link_set = set()

    # 2) First pass: filter sub_links by base_url
    first_pass = filter_urls_by_stem(base_url, sub_links, max_depth=depth)
    link_set.update(first_pass)

    frontier = set(first_pass)

    # 3) Expand up to specified depth
    for depth_level in range(depth):
        next_frontier = set()
        for current_link in frontier:
            current_links, current_content = get_all_links(current_link)
            content_dict_sub[current_link] = current_content

            new_links = set(filter_urls_by_stem(base_url, current_links, max_depth=depth))
            new_links -= link_set

            link_set.update(new_links)
            next_frontier.update(new_links)

        frontier = next_frontier

    for frontier_link in frontier:
        frontier_content = get_content_only(frontier_link)
        content_dict_sub[frontier_link] = frontier_content

    return (link, link_set, content_dict_sub)


def extract_topics(links, base_url):
    second_level_links = []

    for link in links:
        parsed_url = urlparse(link)
        path_parts = parsed_url.path.strip('/').split('/')

        # Ensure the link is from the same domain and meets hierarchy criteria
        if len(path_parts) > 0 and len(path_parts) < 3 and parsed_url.netloc == urlparse(base_url).netloc:
            if path_parts[0] in language_codes and len(path_parts) > 1:
                # Language-specific link with subcategory
                full_link = f"{base_url}/{path_parts[0]}/{path_parts[1]}"
                second_level_links.append(full_link)
            elif path_parts[0] not in language_codes:
                # Link without language prefix
                full_link = f"{base_url}/{path_parts[0]}"
                second_level_links.append(full_link)

    # Remove duplicates
    second_level_links = list(set(second_level_links))

    # Create a DataFrame
    second_level_df = pd.DataFrame(second_level_links, columns=['links'])

    # Extract the topic from the URL
    second_level_df['topic'] = second_level_df['links'].apply(
        lambda x: urlparse(x).path.strip('/').split('/')[-1]
    )
    second_level_df.set_index(['topic'],inplace = True)
    return second_level_df

def preprocess(chosen_links, depth=0):
    start_time = time.time()

    link_library = {}
    content_dict_master = {}

    max_workers = min(8, len(chosen_links))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_link = {
            # Note how we pass `link` as both `link` and `base_url`
            executor.submit(process_link, link, link, depth): link
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

    end_time = time.time()
    print(f"\nPreprocess finished in {end_time - start_time:.2f} seconds")
    return link_library, content_dict_master

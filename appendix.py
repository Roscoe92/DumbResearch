def get_all_links(domain):
    links_to_visit = []

    # # Ensure ChromeDriver is installed and up to date
    chromedriver_autoinstaller.install()

    chrome_driver_path = ""
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service = Service(chrome_driver_path), options = options)

    try:
        driver.get(domain)
        print('page loaded')
        html = driver.page_source
        time.sleep(10)

        soup = BeautifulSoup(html, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            # Resolve relative URLs
            full_url = urljoin(domain, a_tag['href'])
            links_to_visit.append(full_url)


    except Exception as e:
        print(f"Error visiting {full_url}: {e}")

    return links_to_visit

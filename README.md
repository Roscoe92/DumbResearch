# DumbResearch
DumbResearch

DumbResearch is a modular web-scraping and data-extraction framework with an optional Streamlit UI, designed to help users:
	1.	Identify Competitors (via ChatGPT),
	2.	Scrape & Parse competitor websites for further analysis,
	3.	Fetch and Extract reports from government portals (like Bundesanzeiger in Germany).

It leverages:
	•	Python for scripting
	•	Selenium for dynamic web scraping
	•	LangChain / OpenAI for GPT-based text extraction
	•	Bundesanzeiger library (from deutschland package) for fetching German company reports

This project is organized into multiple subfolders and modules to keep logic clean and modular.

Key Folders

	•	scraper/: Core scraping logic (Selenium driver, link extraction).
	•	processing/: Functions for chunking text, sending prompts to GPT, parsing CSV-like outputs.
	•	cli/: Command-line interface versions of competitor research & user interaction flows.
	•	Streamlit/: Multi-page Streamlit web app for an interactive workflow.
	•	country_db/: Bundles country-specific data fetchers like bundesanzeiger.py.

 Installation & Setup

	1.	Clone the Repository
 git clone https://github.com/<YOUR_USERNAME>/DumbResearch.git
  cd DumbResearch

	2.	Create and Activate a Virtual Environment (Optional but recommended)
  python3 -m venv venv
source venv/bin/activate

	3.	Install Dependencies
 pip install -r requirements.txt

 	4.	Set Up Environment Variables (e.g., OpenAI API key)
  export OPENAI_API_KEY="your-key-here"

  	5.	Optional Docker Setup
	•	A Dockerfile is provided. You can build and run the container if you prefer a fully containerized environment.
	•	Example:
 docker build -t dumbresearch .
docker run -p 8501:8501 dumbresearch

Usage

1. CLI Mode

You can run some of the CLI scripts in cli/. For example:
python cli/competitor_research.py

Follow the interactive prompts to identify a target company, find potential competitors via ChatGPT, filter them, etc.

2. Streamlit Multi-Page App

For a friendlier UI, Streamlit pages are in Streamlit/:
	1.	1_competitor_workflow.py – Page 1
	2.	pages/2_scrape_competitors.py – Page 2
	3.	pages/3_bundesanzeiger.py – Page 3

 cd Streamlit
streamlit run 1_competitor_workflow.py

	1.	Page 1 (Competitor Workflow)
	•	Identify the target company, retrieve competitor list from GPT, allow user additions, choose final set.
	2.	Page 2 (Scrape Competitors)
	•	Scrape chosen competitor websites, optionally pick subpages, parse results using GPT, and export to Excel.
	3.	Page 3 (Bundesanzeiger)
	•	Takes the competitor legal entities, fetches their reports from Bundesanzeiger, splits them into relevant financial and qualitative info with GPT, and exports to Excel.

3. Additional Scripts

	•	analysis/analysis.py – Put your deeper analysis or data transformations here.
	•	country_db/ – For country-specific scraping or data retrieval (e.g., Germany’s Bundesanzeiger, UK’s Companies House, etc.).

Features & Highlights

	•	Multi-Stage Flow: Identify competitor set, scrape & parse competitor websites, fetch official business filings, combine & export results.
	•	GPT Integration: Offloads chunked text processing to GPT (via OpenAI) for structured extraction (tables, CSV-like outputs).
	•	Scalable Scraping: Uses Selenium-based parallel crawling (ThreadPoolExecutor) to handle multiple links.
	•	Modular Design: Separation of scraping, processing, user interaction, and data extraction code for easier maintenance.

 Contributing

	1.	Fork the repository on GitHub.
	2.	Create a new feature branch (git checkout -b feature/some-new-feature).
	3.	Commit your changes (git commit -am 'Add some feature').
	4.	Push to your fork (git push origin feature/some-new-feature).
	5.	Create a Pull Request on GitHub for review.

 License

This project is provided under the MIT License 

Contact

	•	Author: Roscoe92
	•	Email: maxpappert4292@gmai.com

import re
import pandas as pd
from processing.extraction import parse_semicolon_csv
from processing.extraction import run_chatgpt

def competitors_with_chatGPT(company, company_context):
    template = (
        f'You are tasked with finding the competitors of a given company called {company}, with the below context provided: {company_context}.'
        'Please follow these instructions carefully: \n\n'
        ' 1. ** Extract Information** : Only extract the information that directly matches the provided description above'
        ' 2. ** Volume** : Find at least 10 competitors for each request.'
        ' 3. ** Empty Response** : If no information matches the description return an empty string'
        ' 4. ** Direct Data** : Your response should contain only data that is explicitly requested, with no other text.'
        ' 5. ** Format** : **Single Table**: Output exactly one table, no extra lines.'
        '  - Use semicolons (`;`) to separate columns.'
        '  - Properly quote cells with ("") if they contain semicolons or commas.'
        '  - If a cell has no data, use `empty`.'
        '  - Columns are the 1) respective competitors ("Competitor"), 2) the industry they are in ("Industry"), 3) the link to their website ("Website"), 4) The name of the legal entity ("Legal entity") 5) The country where the company is registered ("Country")'
        '  - Include the company itself (i.e. whose competitors you are searching) in the tabel as well with all relevant fields populated'
    )
    prompt = template
    print(f"Finding competitors of {company}...")

    parsed_results = []
    try:
        response = run_chatgpt(prompt, model='gpt-4o')
        parsed_results.append(response.choices[0].message.content)
    except Exception as e:
        print(f"Error processing competitor search: {e}")
        parsed_results.append("")

    initial_result = "\n".join(parsed_results)
    return initial_result

def find_competitors():
    company = input('\n**Target**\nEnter the company name you are researching: ')
    company_context = input('\n**Target description**\nEnter context about the company (industry, geographies, etc.): ')
    result_csv = competitors_with_chatGPT(company, company_context)
    result_df = parse_semicolon_csv(result_csv)
    return result_df

def competitor_search_workflow():
    result = find_competitors()
    for i, link in enumerate(result['Website']):
        print(f"{i}: {link}")

    user_input = input(
        "\nThese are the competitors found. "
        "Do you have any additional players to add? "
        "Enter their websites, separated by commas:\n"
    )
    add_players = [str(x.strip().lower().rstrip("/")) for x in user_input.split(",") if x.strip()]
    for i in add_players:
        new_row = {'Competitor': None, 'Industry': None, 'Website': i, 'Legal entity': None}
        result = pd.concat([result, pd.DataFrame([new_row])], ignore_index=True)

    for i, link in enumerate(result['Website']):
        print(f"{i}: {link}")

    user_input = input(
        "\nSelect the indexes of competitors you want to keep, separated by commas:\n> "
    )
    try:
        indexes = [int(x.strip()) for x in user_input.split(",") if x.strip().isdigit()]
    except ValueError:
        print("Invalid input. Please enter a comma-separated list of numbers.")
        return {}

    chosen_competitors = result.iloc[indexes].reset_index(drop=True) if indexes else pd.DataFrame()
    return chosen_competitors

def search_research_workflow():
    from .competitor_research import competitor_search_workflow
    from .user_interaction import dumbresearch_workflow

    competitor_set = competitor_search_workflow()
    print(f"Now looking at competitor websites: {competitor_set['Website']}")
    output = dumbresearch_workflow(competitor_set['Website'])
    return output

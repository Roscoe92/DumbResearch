import os
import re
import time
import pandas as pd
from io import StringIO
from openai import OpenAI

def split_dom_content(dom_content, max_length=8000):
    return [
        dom_content[i : i + max_length]
        for i in range(0, len(dom_content), max_length)
    ]

def preprocess_content(content_dict):
    master_dict = {}
    for key in content_dict.keys():
        master_dict[key] = ''.join(content_dict[key].values())
    return master_dict

def run_chatgpt(prompt, model="gpt-3.5-turbo"):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an advanced data extraction assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    return response

def first_pass_with_chatGPT(dom_chunks):
    """
    Sends chunks of website content to OpenAI's GPT API for parsing based on a description.
    """

    # Loop through chunks and get responses
    parsed_results = []
    # Step 1: Analyze the first chunk with GPT-4o
    first_chunk = dom_chunks[0]
    context_prompt = (
        f"You are tasked with analyzing the following content:\n\n{first_chunk}\n\n"
        "1. Identify the type of business described in the content.\n"
        "2. Determine what is being described (e.g., business's products, infrastructure, locations, or verticals).\n"
        "3. Your output has to be a consise summary of points 1 and 2 in one sentence (not more than 15 words). And clear instructions on which table columns to use to summarise the information (not more than 5 columns)"
        " For example if its product information the columns should be 'product','description','target customers', 'KPIs', if its data centers"
        " the columns should be 'data center','location','Power size in MW', 'size in SQM','customers','expansion capacity' etc.")

    context = run_chatgpt(context_prompt,model = 'gpt-4o')
    context = context.choices[0].message.content

    for i, chunk in enumerate(dom_chunks, start=1):
        template = (
            f'You are tasked with extracting specific information from the following text content: {chunk}.'
            'Please follow these instructions carefully: \n\n'
            ' 1. ** Extract Information** : Only extract the information that directly matches the below description'
            ' 2. ** No Extra Content** : Do not include any additional text, comments or explanations in your response.'
            ' 3. ** Empty Response** : If no information matches the description return to an empty string'
            f' 4. ** Content instructions** : {context}.'
            ' 5. ** Format** : **Single Table**: Output exactly one table, no extra lines or text.'
                            '  - Use semicolons (`;`) to separate columns.'
                            '  - Properly quote cells with ("") if they contain semicolons or commas.'
                            '  - If a cell has no data, use `empty`.'
            )
        prompt = template
        print(f"Processing chunk {i}/{len(dom_chunks)}...")

        try:
            response = run_chatgpt(prompt)
            parsed_results.append(response.choices[0].message.content)

        except Exception as e:
            print(f"Error processing chunk {i}: {e}")
            parsed_results.append("")  # Append an empty string if there's an error

    initial_result = "\n".join(parsed_results)

    return initial_result


def parse_semicolon_csv(llm_output, delimiters=None):
    if delimiters is None:
        delimiters = [",", ";", "\t", "|"]

    pattern = r"```csv\n(.*?)```"
    match = re.search(pattern, llm_output, flags=re.DOTALL | re.IGNORECASE)

    if match:
        csv_text = match.group(1).strip()
    else:
        csv_text = llm_output.strip()

    lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
    csv_text = "\n".join(lines)

    for delimiter in delimiters:
        try:
            df = pd.read_csv(
                StringIO(csv_text),
                sep=delimiter,
                engine="python",
                quotechar='"',
                on_bad_lines="skip"
            )
            if df.shape[1] > 1:
                break
        except Exception:
            continue
    else:
        raise ValueError(
            "Could not parse the table data with any of the specified delimiters or only one column found."
        )

    df.dropna(axis="columns", how="all", inplace=True)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df.columns = [col.strip('" ').strip() for col in df.columns]
    df.reset_index(drop=True, inplace=True)
    return df

def scrape_to_df(content_dict, parse_description):
    start_time = time.time()
    outputs = {}
    master_dict = preprocess_content(content_dict)
    counter = 0
    for key in master_dict:
        counter += 1
        print(f'Processing {key}, {counter} out of {len(master_dict.keys())} datasets to process.')
        dom_content = master_dict[key]
        dom_chunks = split_dom_content(dom_content)
        csv_output = first_pass_with_chatGPT(dom_chunks, parse_description)
        outputs[key] = parse_semicolon_csv(csv_output)
    end_time = time.time()
    print(f"\nParsing scrape results finished in {end_time - start_time:.2f} seconds")
    return outputs

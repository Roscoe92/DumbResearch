import requests
import os
from urllib.parse import urljoin, urlparse

api_key = os.getenv("COMPANIES_HOUSE_API_KEY")

def get_company_number(company_name, api_key):
    """
    Fetches the company number of the first search result for a given company name.

    Args:
        company_name (str): The name of the company to search for.
        api_key (str): Your Companies House API key.

    Returns:
        str: The company number of the first search result.
        None: If no company is found or an error occurs.
    """
    base_url = "https://api.company-information.service.gov.uk"
    search_url = f"{base_url}/search/companies?q={company_name}"

    # Call the search endpoint
    response = requests.get(search_url, auth=(api_key, ''))

    if response.status_code != 200:
        print(f"Error: Search request failed with status code {response.status_code}")
        return None

    data = response.json()

    # Check if the search returned any results
    if "items" not in data or len(data["items"]) == 0:
        print(f"No results found for company name: {company_name}")
        return None

    # Extract the company number of the first result
    company_number = data["items"][0]["company_number"]
    return company_number

def get_filing_history(company_number, api_key):
    """
    Fetches the complete filing history of a company using its company number,
    handling pagination to collect all items.

    Args:
        company_number (str): The unique company number of the company.
        api_key (str): Your Companies House API key.

    Returns:
        list: A complete list of filing history items.
        None: If no filing history is found or an error occurs.
    """
    base_url = "https://api.company-information.service.gov.uk"
    filing_history_url = f"{base_url}/company/{company_number}/filing-history"

    all_items = []  # List to store all filing history items
    start_index = 0  # Initial page index
    items_per_page = 25  # Default items per page (as per Companies House API documentation)

    while True:
        # Add pagination parameters to the request
        params = {
            "start_index": start_index,
            "items_per_page": items_per_page
        }

        # Call the filing history endpoint
        response = requests.get(filing_history_url, params=params, auth=(api_key, ''))

        if response.status_code != 200:
            print(f"Error: Filing history request failed with status code {response.status_code}")
            return None

        data = response.json()

        # Append the items from the current page to the list
        items = data.get("items", [])
        all_items.extend(items)

        # Check if we have fetched all items
        total_count = data.get("total_count", 0)
        if len(all_items) >= total_count:
            break

        # Update the start_index for the next page
        start_index += items_per_page

    return all_items

def get_company_filing_history(company_name, api_key):
    """
    Fetches the filing history of a company using its name.

    Args:
        company_name (str): The name of the company to search for.
        api_key (str): Your Companies House API key.

    Returns:
        dict: Filing history details or an error message.
    """
    # Step 1: Get the company number
    company_number = get_company_number(company_name, api_key)

    if not company_number:
        return {"error": f"Could not find company number for: {company_name}"}

    # Step 2: Get the filing history
    filing_history = get_filing_history(company_number, api_key)

    if not filing_history:
        return {"error": f"Could not retrieve filing history for company number: {company_number}"}

    return {
        "company_name": company_name,
        "company_number": company_number,
        "filing_history": filing_history,
    }

def fetch_document(document_id, api_key, output_path):
    """
    Fetches a document from the Companies House Document API and saves it locally.

    Args:
        document_id (str): The ID of the document to fetch.
        api_key (str): Your Companies House API key.
        output_path (str): The file path (or directory) where the document will be saved.

    Returns:
        bool: True if the document was successfully fetched and saved, False otherwise.
    """
    # If the output path is a directory, append a default filename
    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, f"{document_id}.pdf")

    base_url = "https://document-api.company-information.service.gov.uk"
    document_url = f"{base_url}/document/{document_id}/content"

    # Headers for the request
    headers = {
        "Accept": "application/pdf",  # Request the document as a PDF
    }

    # Send the request to fetch the document
    response = requests.get(document_url, headers=headers, auth=(api_key, ''), allow_redirects=False)

    if response.status_code == 302:  # The document is available
        # Follow the redirect URL in the 'Location' header to download the document
        redirect_url = response.headers.get("Location")
        if not redirect_url:
            print(f"Error: Redirect URL not provided for document_id {document_id}.")
            return False

        # Fetch the document content
        document_response = requests.get(redirect_url)

        if document_response.status_code == 200:
            # Save the document locally
            with open(output_path, "wb") as file:
                file.write(document_response.content)
            print(f"Document {document_id} saved to {output_path}.")
            return True
        else:
            print(f"Error: Failed to fetch document content. Status code {document_response.status_code}.")
            return False

    elif response.status_code == 401:
        print("Error: Unauthorized. Check your API key.")
        return False
    else:
        print(f"Error: Failed to fetch document. Status code {response.status_code}.")
        return False

def fetch_all_and_store(filing_history,path):
    doc_ids = {}
    counter = 0
    # First loop: Extract document IDs
    try:
        for report in filing_history['filing_history']:
            if report.get('category') == 'accounts':
                try:
                    parsed_meta = urlparse(report['links']['document_metadata'])
                    doc_id = parsed_meta.path.split('/')
                    doc_ids[f"{report['date']}: {report['transaction_id']}"] = doc_id[-1]
                    counter += 1

                except KeyError as e:
                    print(f"KeyError while processing report: {e}")
                except Exception as e:
                    print(f"Unexpected error while extracting document ID: {e}")
    except Exception as e:
        print(f"Error in extracting document IDs: {e}")
        return  # Exit the function if the first loop fails

    # Second loop: Fetch and store documents
    try:
        for key, value in doc_ids.items():
            try:
                fetch_document(value, api_key, path)
            except Exception as e:
                print(f"Error fetching document {key} with ID {value}: {e}")
    except Exception as e:
        print(f"Error in fetching and storing documents: {e}")

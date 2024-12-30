import streamlit as st
import pandas as pd

# Adjust these imports to match your package structure
from processing.extraction import parse_semicolon_csv, run_chatgpt

###############################################################################
# The competitor-related functions from your code, adapted to remove raw input.
###############################################################################

def competitors_with_chatGPT(company, company_context):
    template = (
        f'You are tasked with finding the competitors of a given company called {company}, with the below context provided: {company_context}.'
        'Please follow these instructions carefully: \n\n'
        ' 1. ** Extract Information** : Only extract the information that directly matches the provided description above'
        ' 2. ** Volume** : Find at least 10 competitors for the company. Include the company itself as a row in your output table'
        ' 3. ** Empty Response** : If no information matches the description return an empty string'
        ' 4. ** Direct Data** : Your response should contain only data that is explicitly requested, with no other text. No duplications'
        ' 5. ** Format** : **Single Table**: Output exactly one table, no extra lines.'
        '  - Use semicolons (`;`) to separate columns.'
        '  - Properly quote cells with ("") if they contain semicolons or commas.'
        '  - If a cell has no data, use `empty`.'
        '  - Columns are the 1) respective competitors ("Competitor"), 2) the industry they are in ("Industry"), 3) the link to their website ("Website"), 4) The name of the legal entity ("Legal entity")'
    )
    prompt = template
    st.write(f"Finding competitors of {company}...")

    parsed_results = []
    try:
        response = run_chatgpt(prompt, model='gpt-4o')
        parsed_results.append(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Error processing competitor search: {e}")
        parsed_results.append("")

    initial_result = "\n".join(parsed_results)
    return initial_result

def find_competitors(company, context):
    """
    Replaces your original `find_competitors` which used raw input().
    """
    result_csv = competitors_with_chatGPT(company, context)
    result_df = parse_semicolon_csv(result_csv)
    return result_df

###############################################################################
# Streamlit App
###############################################################################

def main():
    st.title("Competitor Search Workflow")
    st.subheader("DumbResearch supports your desk research process by:")
    st.markdown("""
    - ****Finding a company's competitors with you**** (you are here)
    - Summarising the web content of your competitor set (products, locations, etc.)
    - Pulling their filings from Bundesanzeiger and other sources
    """)

    # 1) Enter Company Name and Context
    with st.form("competitor_info"):
        company_name = st.text_input("Enter the company name you are researching:")
        company_context = st.text_area("Enter context about the company (industry, geographies, etc.) and what type of competitors you are interested in:")
        submitted = st.form_submit_button("Find Competitors")

    # Create a session state DataFrame to hold competitor results
    if "competitor_df" not in st.session_state:
        st.session_state.competitor_df = pd.DataFrame()

    if submitted:
        # 2) Run competitor search with ChatGPT
        if not company_name.strip():
            st.warning("Please enter a valid company name.")
        else:
            # Retrieve the competitor DataFrame
            df = find_competitors(company_name, company_context)
            st.session_state.competitor_df = df

    # 3) If we have results in session state, show them
    if not st.session_state.competitor_df.empty:
        st.write("### Competitors Found:")
        st.dataframe(st.session_state.competitor_df)

        # 4) Optionally add more competitors by website
        new_competitors = st.text_input(
            "Add any additional competitors by entering their websites (comma-separated):"
        )
        if st.button("Add Players"):
            add_players = [str(x.strip().lower().rstrip("/")) for x in new_competitors.split(",") if x.strip()]
            for site in add_players:
                new_row = {'Competitor': None, 'Industry': None, 'Website': site, 'Legal entity': None}
                st.session_state.competitor_df = pd.concat([
                    st.session_state.competitor_df,
                    pd.DataFrame([new_row])
                ], ignore_index=True)
            st.success(f"Added {len(add_players)} new players.")

        # Show updated DataFrame
        st.write("### Updated Competitors:")
        st.dataframe(st.session_state.competitor_df)

        # 5) Let user select which rows to keep
        # We'll display indexes in a multi-select
        if not st.session_state.competitor_df.empty:
            all_indexes = range(len(st.session_state.competitor_df))
            chosen_indexes = st.multiselect(
                "Select the competitors you would like to drop:",
                options=all_indexes,
                default=all_indexes  # by default, keep them all
            )

            if st.button("Filter Competitors"):
                try:
                    # Filter the DataFrame by chosen indexes
                    filtered_df = st.session_state.competitor_df.iloc[chosen_indexes].reset_index(drop=True)
                    st.session_state.competitor_df = filtered_df
                    st.success("Competitor list updated.")
                except Exception as e:
                    st.error(f"Error filtering competitors: {e}")

            # Final competitor list
            st.write("### Final Competitor List:")
            st.dataframe(st.session_state.competitor_df)

if __name__ == "__main__":
    main()

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import openai
from openai import OpenAI
import os


template = (
    'You are tasked with extracting specific information from the following text content: {dom_chunks}.'
    'Please follow these instructions carefully: \n\n'
    ' 1. ** Extract Information** : Only extract the information that directly matches the provided description {parse_description}'
    ' 2. ** No Extra Content** : Do not include any additional text, comments or explanations in your response.'
    ' 3. ** Empty Response** : If no information matches the description return to an empty string'
    ' 4. ** Direct Data** : Your response should contain only data that is explicitly requested, with no other text.'
    ' 5. ** Format** : Whenever possible always provide your data as a table with rows and columns.'
)

model = OllamaLLM(model='llama3.2')

def parse_with_ollama(dom_chunks, parse_description):
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model

    parsed_results = []

    for i, chunk in enumerate(dom_chunks, start = 1):
        response = chain.invoke({'dom_chunks' : chunk, 'parse_description' : parse_description })

        print(f'parse batch {i} of {len(dom_chunks)}')
        parsed_results.append(response)

    return '\n'.join(parsed_results)


def parse_with_chatgpt(dom_chunks, parse_description):
       """
       Sends chunks of website content to OpenAI's GPT API for parsing based on a description.
       """

       # Loop through chunks and get responses
       parsed_results = []
       for i, chunk in enumerate(dom_chunks, start=1):
           prompt = template.format(dom_chunks=chunk, parse_description=parse_description)
           print(f"Processing chunk {i}/{len(dom_chunks)}...")

           try:
               client = OpenAI(
                    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)
               response = client.chat.completions.create(
                   model="gpt-3.5-turbo",
                   messages=[
                       {"role": "system", "content": "You are an advanced data extraction assistant."},
                       {"role": "user", "content": prompt}
                   ],
                   temperature=0.0  # For deterministic responses
               )
               if isinstance(response, list):
                    parsed_results.append(response[0].choices[0].message.content)
               else:
                    parsed_results.append(response.choices[0].message.content)

               # Extract the content of the assistant's reply
               parsed_results.append(response[0].choices[0].message.content)

           except Exception as e:
               print(f"Error processing chunk {i}: {e}")
               parsed_results.append("")  # Append an empty string if there's an error

       return "\n".join(parsed_results)

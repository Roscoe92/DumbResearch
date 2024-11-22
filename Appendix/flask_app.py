from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from scrape_logic.scrape import (
    scrape_website,
    split_dom_content,
    clean_body_content,
    extract_body_content,
    get_all_links,
    extract_second_level_headlines,
    re_match_second_level_headlines,
    get_select_data
)
from scrape_logic.parse import parse_with_ollama, parse_with_chatgpt
from download import is_downloadable, download_files
from scrape_logic.user_comms import introduction
import pandas as pd
from io import BytesIO

app = Flask(__name__)

# Session state management
session_state = {
    "second_level_headlines": [],
    "selected_pages": [],
    "dom_content": {}
}

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        action = request.form.get("action")
        domain = request.form.get("domain")

        if action == "parse_website" and domain:
            links = get_all_links(domain)
            session_state["second_level_headlines"] = extract_second_level_headlines(links)
            session_state["downloadable_files"] = is_downloadable(links)
            return redirect(url_for("home"))

        elif action == "scrape_site":
            if session_state["selected_pages"]:
                result = get_select_data(session_state["selected_pages"], domain)
                session_state["dom_content"] = result
                return redirect(url_for("home"))
            else:
                return render_template("index.html", warning="Please select subdomains before scraping.", **session_state)

        elif "select_headline" in request.form:
            headline = request.form.get("select_headline")
            if headline not in session_state["selected_pages"]:
                session_state["selected_pages"].append(headline)
            return redirect(url_for("home"))

        elif "deselect_headline" in request.form:
            headline = request.form.get("deselect_headline")
            if headline in session_state["selected_pages"]:
                session_state["selected_pages"].remove(headline)
            return redirect(url_for("home"))

    return render_template("index.html", **session_state)


@app.route("/parse/<key>", methods=["POST"])
def parse_content(key):
    parse_description = request.form.get(f"description_{key}")
    parser_type = request.form.get(f"parser_type_{key}")

    if parse_description and key in session_state["dom_content"]:
        dom_chunks = split_dom_content(session_state["dom_content"][key])
        if parser_type == "ollama":
            result = parse_with_ollama(dom_chunks, parse_description)
        elif parser_type == "chatgpt":
            result = parse_with_chatgpt(dom_chunks, parse_description)

        # Convert result to DataFrame if applicable
        try:
            table_data = pd.read_csv(BytesIO(result.encode()), sep="\t")  # Adjust separator if needed
            excel_buffer = BytesIO()
            table_data.to_excel(excel_buffer, index=False, engine="xlsxwriter")
            excel_buffer.seek(0)
            return send_file(
                excel_buffer,
                as_attachment=True,
                download_name=f"{key}_table.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception:
            return jsonify({"error": "Could not parse the result as a table."})

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)

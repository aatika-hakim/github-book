import os
from typing import Dict
import streamlit as st
from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain_groq import ChatGroq
from github import Github, GithubException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = "aatika-hakim/book-generator"  # Your GitHub username

# Get API key from environment
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Initialize Groq model
groq_instance = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.5, api_key=GROQ_API_KEY)


# State structure
class BookState:
    def __init__(self, title: str, description: str):
        self.title = title
        self.description = description
        self.table_of_contents = ""
        self.chapters = {}

# Function to generate content
def generate_content(state: BookState):
    prompt = PromptTemplate(
        input_variables=["title", "description"],
        template="Generate a table of contents for a book titled '{title}' with description '{description}'."
    )
    message = HumanMessage(content=prompt.format(title=state.title, description=state.description))
    toc = groq_instance.predict_messages([message]).content.strip()
    return toc

# Push to GitHub
def push_to_github(chapter_name: str, content: str):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)

        # Check for chapters directory
        try:
            repo.get_contents("chapters")
        except GithubException as e:
            if e.status == 404:
                repo.create_file("chapters/.gitkeep", "Create chapters directory", "", branch="main")

        # Check if the file already exists
        try:
            repo.get_contents(f"chapters/{chapter_name}.md")
            return f"File '{chapter_name}.md' already exists. Please use a different name."
        except GithubException as e:
            if e.status == 404:  # File does not exist
                repo.create_file(f"chapters/{chapter_name}.md", f"Add {chapter_name}", content, branch="main")
                return f"Successfully pushed '{chapter_name}' to GitHub."
            else:
                return f"Error checking file existence: {e.data.get('message', 'Unknown error')}"
    except GithubException as e:
        return f"Error pushing to GitHub: {e.data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error: {e}"

# Streamlit user interface
st.set_page_config(page_title="AI Book Generator", page_icon="📚", layout="wide")

# Styling the interface
st.markdown(
    """
    <style>
    .title {
        text-align: center;
        font-size: 2em;
        color: #4CAF50;
    }
    .description {
        text-align: center;
        font-size: 1.2em;
        margin-bottom: 20px;
    }
    .section {
        margin: 20px auto;
        padding: 10px;
        border-radius: 5px;
        background-color: #f9f9f9;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<div class='title'>📚 AI Book Generator</div>", unsafe_allow_html=True)
st.markdown("<div class='description'>Generate and manage your book content easily!</div>", unsafe_allow_html=True)

# User inputs
title = st.text_input("Enter the book title:")
description = st.text_area("Enter the book description:")

if st.button("Generate Table of Contents"):
    if title and description:
        book_state = BookState(title=title, description=description)
        toc = generate_content(book_state)
        st.session_state.table_of_contents = toc
        st.success("Table of Contents generated!")
        st.markdown(f"<div class='section'><strong>Table of Contents:</strong><br>{toc}</div>", unsafe_allow_html=True)
    else:
        st.error("Please provide both title and description.")

# Chapter input
if 'table_of_contents' in st.session_state:
    chapters = st.session_state.table_of_contents.split("\n")
    for chapter in chapters:
        if st.button(f"Generate content for '{chapter}'", key=chapter):
            chapter_content = f"# {chapter}\n\nGenerated content for {chapter}."
            result = push_to_github(chapter, chapter_content)
            st.success(result)
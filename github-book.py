# import os
# from typing import Dict
# import streamlit as st
# from langgraph.graph import StateGraph, END
# from langchain.prompts import PromptTemplate
# from langchain.schema import HumanMessage
# from langchain_groq import ChatGroq
# from github import Github, GithubException
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
# REPO_NAME = "aatika-hakim/book-generator"  # Your GitHub username

# # Get API key from environment
# GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# # Initialize Groq model
# groq_instance = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.5, api_key=GROQ_API_KEY)


# # State structure
# class BookState:
#     def __init__(self, title: str, description: str):
#         self.title = title
#         self.description = description
#         self.table_of_contents = ""
#         self.chapters = {}

# # Function to generate content
# def generate_content(state: BookState):
#     prompt = PromptTemplate(
#         input_variables=["title", "description"],
#         template="Generate a table of contents for a book titled '{title}' with description '{description}'."
#     )
#     message = HumanMessage(content=prompt.format(title=state.title, description=state.description))
#     toc = groq_instance.predict_messages([message]).content.strip()
#     return toc

# # Push to GitHub
# def push_to_github(chapter_name: str, content: str):
#     try:
#         g = Github(GITHUB_TOKEN)
#         repo = g.get_repo(REPO_NAME)

#         # Check for chapters directory
#         try:
#             repo.get_contents("chapters")
#         except GithubException as e:
#             if e.status == 404:
#                 repo.create_file("chapters/.gitkeep", "Create chapters directory", "", branch="main")

#         # Check if the file already exists
#         try:
#             repo.get_contents(f"chapters/{chapter_name}.md")
#             return f"File '{chapter_name}.md' already exists. Please use a different name."
#         except GithubException as e:
#             if e.status == 404:  # File does not exist
#                 repo.create_file(f"chapters/{chapter_name}.md", f"Add {chapter_name}", content, branch="main")
#                 return f"Successfully pushed '{chapter_name}' to GitHub."
#             else:
#                 return f"Error checking file existence: {e.data.get('message', 'Unknown error')}"
#     except GithubException as e:
#         return f"Error pushing to GitHub: {e.data.get('message', 'Unknown error')}"
#     except Exception as e:
#         return f"Error: {e}"

# # Streamlit user interface
# st.set_page_config(page_title="AI Book Generator", page_icon="📚", layout="wide")

# # Styling the interface
# st.markdown(
#     """
#     <style>
#     .title {
#         text-align: center;
#         font-size: 2em;
#         color: #4CAF50;
#     }
#     .description {
#         text-align: center;
#         font-size: 1.2em;
#         margin-bottom: 20px;
#     }
#     .section {
#         margin: 20px auto;
#         padding: 10px;
#         border-radius: 5px;
#         background-color: #f9f9f9;
#         box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# st.markdown("<div class='title'>📚 AI Book Generator</div>", unsafe_allow_html=True)
# st.markdown("<div class='description'>Generate and manage your book content easily!</div>", unsafe_allow_html=True)

# # User inputs
# title = st.text_input("Enter the book title:")
# description = st.text_area("Enter the book description:")

# if st.button("Generate Table of Contents"):
#     if title and description:
#         book_state = BookState(title=title, description=description)
#         toc = generate_content(book_state)
#         st.session_state.table_of_contents = toc
#         st.success("Table of Contents generated!")
#         st.markdown(f"<div class='section'><strong>Table of Contents:</strong><br>{toc}</div>", unsafe_allow_html=True)
#     else:
#         st.error("Please provide both title and description.")

# # Chapter input
# if 'table_of_contents' in st.session_state:
#     chapters = st.session_state.table_of_contents.split("\n")
#     for chapter in chapters:
#         if st.button(f"Generate content for '{chapter}'", key=chapter):
#             chapter_content = f"# {chapter}\n\nGenerated content for {chapter}."
#             result = push_to_github(chapter, chapter_content)
#             st.success(result)


import os
import time
from github import Github, GithubException
from dotenv import load_dotenv
import streamlit as st
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = "aatika-hakim/book-generator"
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Initialize Groq model
groq_instance = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.5, api_key=GROQ_API_KEY)

# Function to generate TOC
def generate_toc(title: str, description: str):
    prompt = PromptTemplate(
        input_variables=["title", "description"],
        template="Generate a table of contents for a book titled '{title}' with description '{description}'."
    )
    message = HumanMessage(content=prompt.format(title=title, description=description))
    toc = groq_instance.predict_messages([message]).content.strip()
    return toc

# Function to check GitHub rate limit
def check_rate_limit():
    g = Github(GITHUB_TOKEN)
    rate_limit = g.get_rate_limit()
    core_rate_limit = rate_limit.core
    st.write(f"Rate limit: {core_rate_limit.remaining}/{core_rate_limit.limit} remaining.")
    if core_rate_limit.remaining == 0:
        st.error("Rate limit exceeded. Please try again later.")
        return False
    return True

# Exponential backoff function
def exponential_backoff(attempt):
    wait_time = 2 ** attempt  # Exponential backoff
    st.write(f"Waiting {wait_time} seconds before retrying...")
    time.sleep(wait_time)
def push_to_github_with_retries(chapter_name: str, content: str, retries=2):
    for attempt in range(retries):
        if not check_rate_limit():
            exponential_backoff(attempt)
            continue

        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            st.write(f"Accessing repo: {repo.full_name}")

            # Check for chapters directory
            try:
                repo.get_contents("chapters")
                st.write("Chapters directory exists.")
            except GithubException as e:
                if e.status == 404:
                    st.write("Chapters directory not found. Creating it.")
                    repo.create_file("chapters/.gitkeep", "Create chapters directory", "", branch="main")
                    st.write("Chapters directory created.")

            # Check if the file already exists
            try:
                repo.get_contents(f"chapters/{chapter_name}.md")
                st.warning(f"File '{chapter_name}.md' already exists. Please use a different name.")
                return f"File '{chapter_name}.md' already exists."
            except GithubException as e:
                if e.status == 404:  # File does not exist
                    st.write(f"Creating file: chapters/{chapter_name}.md")
                    response = repo.create_file(f"chapters/{chapter_name}.md", f"Add {chapter_name}", content, branch="main")
                    st.write(f"Response: {response}")
                    return f"Successfully pushed '{chapter_name}' to GitHub."
                else:
                    st.error(f"Error checking file existence: {e.data.get('message', 'Unknown error')} (Status: {e.status})")
                    return f"Error checking file existence: {e.data.get('message', 'Unknown error')} (Status: {e.status})"

        except GithubException as e:
            st.error(f"Error pushing to GitHub: {e.data.get('message', 'Unknown error')} (Status: {e.status})")
            exponential_backoff(attempt)
        except Exception as e:
            st.error(f"Error: {e}")
            return f"Error: {e}"

    return "Failed to push after several retries."


# Define a simple state schema as a class
class LearningState:
    def __init__(self):
        self.user_input = ""  # User input
        self.generated_output = ""  # Generated output

# Initialize StateGraph with the defined state schema
builder: StateGraph = StateGraph(state_schema=LearningState)

# Add nodes to the graph
builder.add_node("input_state", lambda: "Waiting for user input")
builder.add_node("toc_generated_state", lambda: "Table of Contents generated")
builder.add_node("generating_content_state", lambda: "Generating content for chapters")

# Define edges
builder.add_edge(START, "input_state")
builder.add_edge("input_state", "toc_generated_state")
builder.add_edge("toc_generated_state", "generating_content_state")
builder.add_edge("generating_content_state", END)

# Compile the graph
graph: CompiledStateGraph = builder.compile()

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

# Initialize state in session if not present
if 'current_state' not in st.session_state:
    st.session_state.current_state = "input_state"

# User inputs
title = st.text_input("Enter the book title:")
description = st.text_area("Enter the book description:")

# Generate Table of Contents
if st.button("Generate Table of Contents") and st.session_state.current_state == "input_state":
    if title and description:
        toc = generate_toc(title, description)
        st.session_state.table_of_contents = toc
        st.success("Table of Contents generated!")
        st.markdown(f"<div class='section'><strong>Table of Contents:</strong><br>{toc}</div>", unsafe_allow_html=True)
        # Transition state
        st.session_state.current_state = "toc_generated_state"
    else:
        st.error("Please provide both title and description.")

# Generate content for each chapter and push to GitHub
if 'table_of_contents' in st.session_state and st.session_state.current_state == "toc_generated_state":
    chapters = [chapter for chapter in st.session_state.table_of_contents.split("\n") if chapter.strip()]
    for i, chapter in enumerate(chapters):
        chapter_key = f"push_{i}"
        
        if st.button(f"Push to GitHub '{chapter}'", key=chapter_key):
            chapter_name = chapter.replace(" ", "_")  # Replace spaces with underscores for file names
            chapter_content = f"# {chapter}\n\nGenerated content for {chapter}."
            result = push_to_github_with_retries(chapter_name, chapter_content)
            st.success(result)
            # Transition state (if necessary)
            st.session_state.current_state = "generating_content_state"


# Display current state for debugging
st.write(f"Current state: {st.session_state.current_state}")

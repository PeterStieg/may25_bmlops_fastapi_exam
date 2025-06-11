import streamlit as st
import pandas as pd
import numpy as np

import aiohttp
import json
import random

from typing import Dict, List

# Importing the requests library for making HTTP requests
import requests
import asyncio
import aiohttp


def get_registered_users(file_path: str = "registered_users.json") -> dict:
    """
    Reads registered users from a JSON file.

    Args:
        file_path (str): Path to the JSON file containing registered users.

    Returns:
        dict: Dictionary containing registered users. If the file does not exist,
            an empty dictionary is returned.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            registered_users = json.load(file)

    except FileNotFoundError:
        print("File with registered users not found. Please check the file path.")
        registered_users = {}

    return registered_users


# Check if the Streamlit app is running
async def check_streamlit_status(streamlit_url: str = "http://localhost:8501") -> bool:
    """
    Checks if the Streamlit app is accessible by making a quick HTTP request.

    We use async here so our main FastAPI route doesn't get blocked waiting for the response.
    """
    try:
        # Create an async HTTP session with a short timeout
        # We don't want to keep users waiting if Streamlit is slow to respond
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=3)
        ) as session:
            async with session.get(streamlit_url) as response:
                # If we get any response (even an error page), Streamlit is running
                return response.status < 500
    except Exception:
        # If we can't connect at all, Streamlit is offline
        return False


# Function to get button configurations based on service availability
def get_button_config(
    is_streamlit_online: bool,
    base_url: str = "https://may-25-bmlops-fastapi.streamlit.app/",
) -> List[Dict[str, str]]:
    """
    Returns a list of button configurations based on service availability.

    Each button is represented as a dictionary with 'url', 'text', and 'description' keys.
    """
    # These three buttons are always available since they're part of FastAPI itself
    buttons = [
        {
            "url": f"{base_url}/docs",
            "text": "FastAPI Docs",
            "description": "Interactive API documentation with Swagger UI",
        },
        {
            "url": f"{base_url}/redoc",
            "text": "FastAPI ReDoc",
            "description": "Alternative API documentation with ReDoc interface",
        },
        {
            "url": f"{base_url}/openapi.json",
            "text": "OpenAPI Schema",
            "description": "Raw OpenAPI/Swagger specification in JSON format",
        },
    ]

    # Add Streamlit button if service is accessible
    if is_streamlit_online:
        streamlit_button = {
            "url": "https://may-25-bmlops-fastapi.streamlit.app/",
            "text": "Streamlit",
            "description": "Interactive Streamlit application for FastAPI exam",
        }
        return buttons + [streamlit_button]

    return buttons


# pandas // DataFrame functions


# Load the questions DataFrame from an Excel file
def get_DataFrame_from_Excel(file_path="questions_en.xlsx") -> pd.DataFrame:
    """
    Load a DataFrame from an Excel file.

    Args:
        file_path (str): Path to the Excel file.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """

    questions_df = pd.read_excel(file_path)

    # Replace NaN with None for JSON serialization
    questions_df = questions_df.replace({np.nan: None})
    questions_df.index.name = "nr"

    questions_df.sort_values(by="nr", inplace=True, ascending=True)

    # Increment index by 1 if lowest index is 0
    if questions_df.index.min() == 0:
        questions_df.index = questions_df.index + 1

    return questions_df


def get_unique_col_values(df, col_name):
    unique_list = sorted(df[col_name].unique())
    return unique_list


def generate_random_question_indices(question_count_db, question_count_quiz):
    question_indices = random.sample(range(0, question_count_db), question_count_quiz)
    return question_indices


def get_random_questions_df(df, q_c_q):
    r_q_df = df.copy()

    question_count_db = r_q_df.shape[0]

    if q_c_q == "All":
        question_count_quiz = question_count_db
        r_q_df = r_q_df.sample(question_count_quiz)

    elif q_c_q.isdigit():
        question_count_quiz = int(q_c_q)
        if question_count_quiz > question_count_db:
            r_q_df = r_q_df.sample(question_count_quiz, replace=True)
        else:
            r_q_df = r_q_df.sample(question_count_quiz)

    r_q_df = r_q_df.sample(question_count_quiz)
    return r_q_df


# Define the callback function that will run when any response changes
def update_correct_box_options():
    """
    This function rebuilds the correct_box_options list based on
    which response fields currently have content.

    It runs automatically whenever any response field changes.
    """
    # Start with an list
    options = ["None"]

    # Check each response field in session state and add to options if filled
    if (
        st.session_state.get("responseA_key", "")
        and st.session_state.get("responseA_key", "").strip()
    ):
        options.append("A")

    if (
        st.session_state.get("responseB_key", "")
        and st.session_state.get("responseB_key", "").strip()
    ):
        options.append("B")

    if (
        st.session_state.get("responseC_key", "")
        and st.session_state.get("responseC_key", "").strip()
    ):
        options.append("C")

    if (
        st.session_state.get("responseD_key", "")
        and st.session_state.get("responseD_key", "").strip()
    ):
        options.append("D")

    # Update the session state with our new options
    st.session_state.correct_box_options = options


# Check if all required fields are filled
def check_upload_requirements(q_t, q_s_b, q_u_b, r_a, r_b) -> bool:
    """
    Check if the required fields (question, category, test type, and both answers) are properly filled.
    Returns True if all required fields have valid values, False otherwise.
    """
    return not (
        q_t is not None
        and q_t.strip() != ""  # Question text is not empty
        and q_s_b is not None  # Category is selected
        and q_u_b is not None  # Test type is selected
        and r_a is not None
        and r_a.strip() != ""  # Response A is not empty
        and r_b is not None
        and r_b.strip() != ""  # Response B is not empty
    )


def json_to_df(json_string: dict) -> pd.DataFrame:
    """
    Convert a JSON string to a DataFrame.

    Args:
        json_string (dict): JSON string to be converted.

    Returns:
        pd.DataFrame: DataFrame created from the JSON string.
    """
    df = pd.json_normalize(json_string["new_question"])
    df.set_index("nr", inplace=True)

    return df


def get_all_questions_df(new_question_dict: dict) -> pd.DataFrame:

    questions_df = get_DataFrame_from_Excel()
    new_question_df = json_to_df(new_question_dict)

    # Ensure new_question_df has the same columns as questions_df
    new_question_df = new_question_df[questions_df.columns.tolist()]

    all_questions_df = pd.concat([questions_df, new_question_df])

    all_questions_df.sort_values(by="nr", inplace=True, ascending=False)

    return all_questions_df


def save_all_questions_df(
    df: pd.DataFrame, file_path: str = "questions_en.xlsx"
) -> None:
    """
    Save the DataFrame to an Excel file.
    Args:
        df (pd.DataFrame): DataFrame to be saved.
        file_path (str): Path to the Excel file where the DataFrame will be saved.
    """
    df.sort_values(by="nr", inplace=True, ascending=True)
    df.to_excel(file_path, index=False, engine="openpyxl")


# Function to return a simple greeting message
def hw() -> str:
    """
    A simple function that returns a greeting message.

    Returns:
        str: Greeting message.
    """
    return "Hello World!"

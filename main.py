import pandas as pd
import numpy as np

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from utils import (
    check_streamlit_status,
    get_button_config,
    get_DataFrame_from_Excel,
    get_registered_users,
    get_random_questions_df,
    get_unique_col_values,
)


# Create a FastAPI instance
api = FastAPI(
    title="MAY25 BMLOPS // FastAPI",
    description="FastAPI app returning random questions via endpoints or Streamlit app.",
    version="0.0.1",
)


# Jinja2 // Create a Jinja2Templates instance for rendering HTML templates
templates = Jinja2Templates(directory="templates")

# Mount static files directory - this makes files in "static" folder accessible via URL
api.mount("/static", StaticFiles(directory="static"), name="static")


@api.get("/", name="Project landing page", response_class=HTMLResponse)
async def get_index(request: Request) -> HTMLResponse:
    """
    The "index" route returns an HTML page rendered with jinja2.

    The page contains buttons with links to FastAPI's documentation: docs, redocs, and openapi.json.

    If a Streamlit app is online it will be linked as well.

    Returns:
        HTMLResponse: An HTML page rendered with Jinja2Templates.
    """

    # Check asynchronously if Streamlit is online
    streamlit_online = await check_streamlit_status()

    # Generate the appropriate button configuration
    buttons = get_button_config(streamlit_online)

    # The template can receive data to customize the page
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "MAY25 BMLOPS // FastAPI",
            "streamlit_online": streamlit_online,
            "buttons": buttons,
        },
    )


@api.get("/registered_users", name="Get registered users")
def get_registered_users_from_file() -> dict:
    """
    The "registered_users" route returns a list of registered users saved locally in a JSON file.

    This route is used to check if a user is registered and to validate login credentials.

    Returns:
        dict: Dictionary of all registered users with their passwords.
    """
    registered_users = get_registered_users()

    return registered_users


@api.get("/check_user_login", name="Check user login")
def check_user_login(request: Request) -> str:
    """
    The 'check_user_login' route checks if the provided user name and password
    from headers match a registered user.

    Args:
        request (Request): The FastAPI request object containing headers.

    Returns:
        str: Returns "admin" if the user is an admin, "user" if the user is registered,
        "no_login_info" if credentials are missing, "login_failed" if credentials don't match.
    """
    # Extract credentials from headers
    user_name = request.headers.get("X-Username", "")
    password = request.headers.get("X-Password", "")

    registered_users = get_registered_users()

    if user_name == "" or password == "":
        return "no_login_info"
    elif user_name == "admin" and password == "4dm1n":
        return "admin"
    elif user_name in registered_users and password == registered_users[user_name]:
        return "user"
    else:
        return "login_failed"


@api.get("/test_types", name="Get test types")
def get_test_types():
    """
    The "test_types" route returns a list of unique test types which are available.

    Returns:
        list: List of all available test types.
    """

    questions_df = get_DataFrame_from_Excel()

    test_types = get_unique_col_values(questions_df, "use")

    return test_types


@api.get("/categories", name="Get categories")
def get_categories():
    """
    The "categories" route returns a list of unique categories which are available.

    Returns:
        list: List of all available categories.
    """
    questions_df = get_DataFrame_from_Excel()

    categories = get_unique_col_values(questions_df, "subject")

    return categories


@api.get(
    "/questions",
    name="Get DataFrame with questions",
)
def get_questions_endpoint(
    subject: str = "All", use: str = "All", question_count: str = "All"
):
    """
    The "questions" route returns either a DataFrame with all questions or a filtered DataFrame with random questions based on test type 'use' and test category 'subject' and "question_count".

    Args:
        subject (str): The category to filter by (default is "All").
        use (str): The test type to filter questions by (default is "All").
        question_count (int): The number of random questions to return (default is "All").

    Returns:
        dict: A dictionary containing the selected questions.
    """
    questions_df = get_DataFrame_from_Excel()

    if use == "All" and subject == "All" and question_count == "All":

        # Convert DataFrame to dictionary for JSON serialization
        return {"questions": questions_df.to_dict(orient="records")}

    else:
        random_questions_df = questions_df.copy()

        if use != "All":
            use_mask = questions_df["use"] == use
            random_questions_df = random_questions_df[use_mask]

        if subject != "All":
            subject_list = subject.split(",") if subject.count(",") > 0 else [subject]
            subject_mask = questions_df["subject"].isin(subject_list)
            random_questions_df = random_questions_df[subject_mask]

        random_questions_df = get_random_questions_df(
            random_questions_df, question_count
        )

        return {"questions": random_questions_df.to_dict(orient="records")}


@api.post("/add_question", name="Add new question to database")
def add_question(request: Request, question_dict: dict) -> dict:
    """
    The "add_question" route allows an admin user to add a new question to the
    questions DataFrame and save it as Excel file.

    Args:
        request (Request): The FastAPI request object containing headers with credentials.
        new_question (list): The new question's details

    Returns:
        dict: A dictionary containing the status of the operation and the new question.
    """
    # Extract credentials from headers
    user_name = request.headers.get("X-Username", "")
    password = request.headers.get("X-Password", "")

    # Check if the user is an admin
    if not (user_name == "admin" and password == "4dm1n"):
        return {
            "status": "error",
            "message": "Unauthorized: Admin credentials required",
        }

    if not question_dict or len(question_dict) == 0:
        return {
            "status": "error",
            "message": "No question data provided",
        }

    return {
        "status": "success",
        "message": "Question received successfully",
        "question": question_dict,
    }

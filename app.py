# Home.py
import streamlit as st
import pandas as pd
import requests

from utils import (
    check_upload_requirements,
    get_all_questions_df,
    get_DataFrame_from_Excel,
    save_all_questions_df,
    update_correct_box_options,
)

st.set_page_config(
    page_title="DataScientest // FastAPI exam",
    page_icon="static/favicon.png",
    layout="wide",
)

# Title
st.title(f"DataScientest // FastAPI exam")

questions_df = get_DataFrame_from_Excel()
questions_count_db = questions_df.shape[0]

api_error = False
login_type = None
upload_requirements = False

# Initialize session state for correct_box_options if it doesn't exist
if "correct_box_options" not in st.session_state:
    st.session_state.correct_box_options = ["None"]

# Fetching test types and categories from the FastAPI server
try:
    categories = requests.get("https://fastapi-j6h5.onrender.com/categories").json()
    categories_ui = ["All"] + categories

    test_types = requests.get("https://fastapi-j6h5.onrender.com/test_types").json()
    test_types_ui = ["All"] + test_types

    registered_users = requests.get(
        "https://fastapi-j6h5.onrender.com/registered_users"
    ).json()

except requests.exceptions.RequestException:
    st.error(f"The FastAPI server is not running or not reachable.", icon="🚨")
    st.info("Restart the API server and try again.", icon="ℹ️")
    st.code("python3 -m uvicorn main:api --reload", language="bash")

    # If the API call fails, we set default values for test types and categories
    test_types_ui = []
    categories_ui = []

    api_error = True


if api_error == False:

    # Home page content
    with st.expander(label="**Login**", expanded=True):

        # Create a horizontal container with columns
        ul_col1, ul_col2 = st.columns(2)  # ul_ as in "user login"

        # Text input for user name and password
        with ul_col1:

            user_name = st.text_input(
                label="**User name**",
                help="Enter user name.",
            )

        with ul_col2:
            password = st.text_input(
                label="**Password**",
                help="Enter password.",
            )

    # Authentication check
    # Create headers dictionary for authentication
    auth_headers = {
        "X-Username": user_name,
        "X-Password": password,
    }

    # Send request with headers
    response = requests.get(
        "https://fastapi-j6h5.onrender.com/check_user_login", headers=auth_headers
    )

    login_type = response.json()

    if login_type == "no_login_info":
        st.info("**Login info needed:** Please enter your credentials.", icon="ℹ️")
    elif login_type == "admin":
        st.success("**Admin login** successful!", icon="👨🏻‍💻")
    elif login_type == "user":
        st.success("**User login** successful!", icon="✅")
    else:
        st.warning("**Login info failed:** Please check your credentials.", icon="🚨")

    if login_type == "admin" or login_type == "user":
        st.markdown(
            "This section allows registered users to select the test type `use`, the category `subject` and the number of random questions."
        )

        with st.expander("**Options** for API query", expanded=True):

            # Create a horizontal container with columns
            as_col1, as_col2, as_col3 = st.columns(3)  # as_ as in "API settings"

            # Check boxes for categories
            with as_col1:
                subject_box = st.multiselect(
                    label="**Category**",
                    options=categories_ui,
                    default="All",
                    placeholder="All",
                    help="Select the categories you want to focus on.",
                )

            # Drop down menu for test type (use)
            with as_col2:

                use_box = st.selectbox(
                    label="**Test type**",
                    options=test_types_ui,
                    placeholder="All",
                    help="Select the test type you want to train for.",
                )

            # Radio button for number of questions
            with as_col3:
                number_radio = st.radio(
                    "**Number** of random questions",
                    ("All", "5", "10", "20"),
                    horizontal=True,
                    help="Select the number of random questions you want to see. **Note:** If the selected number is larger than the available questions, questions will be resampled.",
                )

        # Prepare the query string for the API request
        test_type_str = use_box.replace(" ", "+")
        test_categories_str = ",".join(subject_box)
        question_count_str = number_radio

        query_string = f"https://fastapi-j6h5.onrender.com/questions?use={test_type_str}{'&subject=' + f'{test_categories_str}' if subject_box != [] else ''}&question_count={question_count_str}"

        # Get the DataFrame from the API
        questions_json = requests.get(query_string)
        questions_dict = questions_json.json()["questions"]
        questions_df = pd.DataFrame(questions_dict)

        # Rename and shift the index
        questions_df.index.name = "nr"
        questions_df.index = questions_df.index + 1

        if (
            test_type_str == "All"
            and test_categories_str == "All"
            and question_count_str == "All"
        ):
            filtered_df = False
        else:
            filtered_df = True

        with st.expander(
            f"**DataFrame** with {'filtered, random' if filtered_df else 'all'} questions",
            expanded=True,
        ):

            st.dataframe(questions_df)

        with st.expander(
            "**API query** for FastAPI endpoint",
            expanded=True,
        ):
            st.code(query_string)

        if user_name == "admin" and password == "4dm1n":

            with st.expander(
                label="**Admin feature #1:** Add new question", expanded=True
            ):
                # Create a layout of first row with columns for the admin data entry
                (
                    nr_col,
                    question_col,
                    subject_col,
                    use_col,
                    remark_col,
                ) = st.columns(5)

                with nr_col:
                    st.markdown("**nr**")
                    st.text(str(questions_count_db + 1))

                with question_col:
                    question_text = st.text_input(
                        label="**Question*** (required)",
                        placeholder="Enter question",
                        help="Enter question.",
                        value=None,
                    )

                with subject_col:
                    question_subject_box = st.selectbox(
                        label="**Category*** (required)",
                        options=categories,
                        placeholder="Select categories",
                        help="Select the category the question belongs to.",
                        index=None,
                    )

                with use_col:
                    question_use_box = st.selectbox(
                        label="**Test type*** (required)",
                        options=test_types,
                        placeholder="Select test type",
                        help="Select the test type the question belongs to.",
                        index=None,
                    )

                with remark_col:
                    remark_text = st.text_input(
                        label="**remark** (optional)",
                        placeholder="Enter remark",
                        help="Enter any necessary remarks.",
                        value=None,
                    )

                # Create a layout of first row with columns for the admin data entry
                (
                    correct_col,
                    responseA_col,
                    responseB_col,
                    responseC_col,
                    responseD_col,
                ) = st.columns(5)

                with correct_col:
                    correct_box = st.multiselect(
                        label="**correct**",
                        options=st.session_state.correct_box_options,
                        placeholder="Select correct response",
                        help="Select the question's correct responses.",
                        default=["None"],
                    )

                with responseA_col:
                    responseA_text = st.text_input(
                        label="**responseA*** (required)",
                        placeholder="Enter responseA",
                        help="Enter the text for responseA.",
                        value=None,
                        key="responseA_key",  # Unique key for this input
                        on_change=update_correct_box_options,  # Call function when this changes
                    )

                with responseB_col:
                    responseB_text = st.text_input(
                        label="**responseB*** (required)",
                        placeholder="Enter responseB",
                        help="Enter the text for responseB.",
                        value=None,
                        key="responseB_key",  # Unique key for this input
                        on_change=update_correct_box_options,  # Call function when this changes
                    )

                with responseC_col:
                    responseC_text = st.text_input(
                        label="**responseC** (optional)",
                        placeholder="Enter responseC",
                        help="Enter the text for responseC.",
                        value=None,
                        key="responseC_key",  # Unique key for this input
                        on_change=update_correct_box_options,  # Call function when this changes
                    )

                with responseD_col:
                    responseD_text = st.text_input(
                        label="**responseD** (optional)",
                        placeholder="Enter responseD",
                        help="Enter the text for responseD.",
                        value=None,
                        key="responseD_key",  # Unique key for this input
                        on_change=update_correct_box_options,  # Call function when this changes
                    )

                if (len(correct_box) > 1) and ("None" in correct_box):
                    correct_box.remove("None")

                # Convert the DataFrame to a dictionary for JSON serialization
                new_question_dict = {
                    "new_question": {
                        "nr": questions_count_db + 1,
                        "question": question_text if question_text else None,
                        "subject": (
                            question_subject_box if question_subject_box else None
                        ),
                        "use": question_use_box if question_use_box else None,
                        "responseA": responseA_text if responseA_text else None,
                        "responseB": responseB_text if responseB_text else None,
                        "responseC": responseC_text if responseC_text else None,
                        "responseD": responseD_text if responseD_text else None,
                        "correct": (
                            (", ").join(correct_box) if len(correct_box) > 1 else "None"
                        ),
                        "remark": remark_text if remark_text else None,
                    },
                }

                if check_upload_requirements(
                    question_text,
                    question_subject_box,
                    question_use_box,
                    responseA_text,
                    responseB_text,
                ):
                    st.button(
                        "Add question to database (not available: enter required fields*)",
                        type="secondary",
                        use_container_width=True,
                        help="Insert required fields* before adding question to database",
                    )

                else:
                    upload_requirements = True
                    if st.button(
                        "Add question to database",
                        type="primary",
                        use_container_width=True,
                        help="Click to add the new question to the database",
                    ):

                        # Send the new question to the FastAPI server
                        # Create headers dictionary for authentication
                        auth_headers = {
                            "X-Username": user_name,
                            "X-Password": password,
                        }

                        # Send request with headers instead of parameters
                        response = requests.post(
                            "https://fastapi-j6h5.onrender.com/add_question",
                            headers=auth_headers,
                            json=new_question_dict,
                        )

                        response_data = response.json()
                        st.toast(response_data, icon="✅")

            with st.expander(
                label="**Admin feature #2:** Show new DataFrame with all questions _(if applicable)_",
                expanded=True,
            ):
                if upload_requirements == False:
                    st.info("Please enter required fields of new question", icon="ℹ️")
                else:
                    all_questions_df = get_all_questions_df(new_question_dict)
                    st.dataframe(all_questions_df)

            with st.expander(
                label="**Admin feature #3:** Save DataFrame with all questions",
                expanded=True,
            ):
                if upload_requirements == False:
                    st.button(
                        "Save DataFrame with all questions (not available)",
                        type="secondary",
                        use_container_width=True,
                        help="Insert required fields* before saving the DataFrame with all questions",
                    )
                else:
                    if st.button(
                        "Save DataFrame with all questions",
                        type="primary",
                        use_container_width=True,
                        help="Click to save the DataFrame with all questions to an Excel file",
                    ):
                        save_all_questions_df(all_questions_df)

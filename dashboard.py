import streamlit as st
import pandas as pd
import plotly.express as px
import chardet
import pymysql
import bcrypt
import re
import os
import traceback
import matplotlib.pyplot as plt
from io import BytesIO


# Set page configuration
st.set_page_config(page_title="User Management System", page_icon=":bar_chart:", layout="wide")

# Environment variables (use these in a real application)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'RBI')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', '')

# Initialize the admin password hash if not set
if not ADMIN_PASSWORD_HASH:
    ADMIN_PASSWORD_HASH = bcrypt.hashpw('RBI123'.encode(), bcrypt.gensalt()).decode()

# Database connection function
def create_connection():
    try:
        return pymysql.connect(
            host='localhost',
            user='root',
            password='',  # Update this if you have a password set for MySQL
            database='user_db',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.MySQLError as e:
        st.error(f"Database connection error: {e}")
        return None

# Function to hash passwords
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Function to verify passwords
def verify_password(stored_hash, password):
    return bcrypt.checkpw(password.encode(), stored_hash.encode())

# Function to validate email
def is_valid_email(email):
    email_regex = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return email_regex.match(email) is not None

# Function to validate phone number
def is_valid_phone(phone):
    phone_regex = re.compile(r"^\+?[1-9]\d{9}$")
    return phone_regex.match(phone) is not None

# Function to check if a username or email already exists
def check_existing_user(username, email, phone):
    connection = create_connection()
    if not connection:
        return True  # Prevent further operations if connection fails
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE username = %s OR email = %s OR phone_number = %s"
            cursor.execute(sql, (username, email, phone))
            result = cursor.fetchall()
            return len(result) > 0
    except pymysql.MySQLError as e:
        st.error(f"Database Error: {e}")
        return True
    finally:
        connection.close()

# Function to register a new user
def register_user(username, first_name, last_name, email, phone_number, password):
    if not is_valid_email(email):
        st.error("Invalid email format!")
        return
    if not is_valid_phone(phone_number):
        st.error("Invalid phone number format!")
        return
    if check_existing_user(username, email, phone_number):
        st.error("Username, email, or phone number already in use!")
        return
    
    connection = create_connection()
    if not connection:
        st.error("Unable to connect to the database.")
        return
    try:
        with connection.cursor() as cursor:
            sql = """INSERT INTO users 
                     (username, first_name, last_name, email, phone_number, password) 
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            values = (username, first_name, last_name, email, phone_number, hash_password(password))
            cursor.execute(sql, values)
            connection.commit()
            st.success("Registration successful!")
            go_to_login()
    except pymysql.MySQLError as e:
        st.error(f"Database Error: {e}")
    finally:
        connection.close()

# Function to authenticate a user
def authenticate_user(username, password):
    connection = create_connection()
    if not connection:
        return False
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
            if user and verify_password(user['password'], password):
                return True
            return False
    except pymysql.MySQLError as e:
        st.error(f"Database Error: {e}")
        return False
    finally:
        connection.close()

# Function to check if the user is an admin
def is_admin(username, password):
    return username == ADMIN_USERNAME and verify_password(ADMIN_PASSWORD_HASH, password)

# Function to get all users
def get_all_users():
    connection = create_connection()
    if not connection:
        return []
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users"
            cursor.execute(sql)
            return cursor.fetchall()
    except pymysql.MySQLError as e:
        st.error(f"Database Error: {e}")
        return []
    finally:
        connection.close()

# Function to update user details
def update_user(username, first_name, last_name, email, phone_number, password=None):
    connection = create_connection()
    if not connection:
        st.error("Unable to connect to the database.")
        return
    try:
        with connection.cursor() as cursor:
            if password:
                hashed_password = hash_password(password)
                sql = """UPDATE users 
                         SET first_name = %s, last_name = %s, email = %s, phone_number = %s, password = %s
                         WHERE username = %s"""
                values = (first_name, last_name, email, phone_number, hashed_password, username)
            else:
                sql = """UPDATE users 
                         SET first_name = %s, last_name = %s, email = %s, phone_number = %s
                         WHERE username = %s"""
                values = (first_name, last_name, email, phone_number, username)
            cursor.execute(sql, values)
            connection.commit()
            st.success("User updated successfully!")
    except pymysql.MySQLError as e:
        st.error(f"Database Error: {e}")
    finally:
        connection.close()

# Function to delete a user
def delete_user(username):
    connection = create_connection()
    if not connection:
        st.error("Unable to connect to the database.")
        return
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            connection.commit()
            st.success("User deleted successfully!")
    except pymysql.MySQLError as e:
        st.error(f"Database Error: {e}")
    finally:
        connection.close()
        
# Function to detect encoding
def detect_encoding(file):
    raw_data = file.read(10000)  # Read the first 10,000 bytes to detect encoding
    result = chardet.detect(raw_data)
    encoding = result['encoding']
    file.seek(0)  # Reset file pointer to the beginning
    return encoding

# Function to read file
def read_file(file):
    try:
        if file.type == "text/csv":
            encoding = detect_encoding(file)
            df = pd.read_csv(file, encoding=encoding)
        elif file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            df = pd.read_excel(file, engine='openpyxl')
        else:
            st.error("Unsupported file type.")
            return None
        return df
    except pd.errors.ParserError:
        st.error("Error parsing the file. Please check the file format.")
        return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

# Define session state for user login and page view
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None

if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

if 'page' not in st.session_state:
    st.session_state.page = 'register'  # Default to registration page

if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

# Navigation functions
def go_to_register():
    st.session_state.page = 'register'

def go_to_login():
    st.session_state.page = 'login'

def go_to_main():
    st.session_state.page = 'main'

def go_to_edit_profile():
    st.session_state.page = 'edit_profile'

def go_to_admin_panel():
    st.session_state.page = 'admin_panel'

def go_to_admin_login():
    st.session_state.page = 'admin_login'

def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.admin_authenticated = False
    st.session_state.uploaded_file = None
    go_to_login()



# Page routing
try:
    if st.session_state.page == 'register':
        st.header("Register")
        
        new_username = st.text_input("New Username", key='new_username')
        new_name = st.text_input("First Name", key='new_name')
        new_last_name = st.text_input("Last Name", key='new_last_name')
        new_email = st.text_input("Email", key='new_email')
        new_phone = st.text_input("Phone", key='new_phone')
        new_password = st.text_input("New Password", type="password", key='new_password')
        confirm_password = st.text_input("Confirm Password", type="password", key='confirm_password')

        if st.button("Register", key='register_button'):
            if not (new_username and new_name and new_last_name and new_email and new_phone and new_password and confirm_password):
                st.error("All fields are required.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif not is_valid_email(new_email):
                st.error("Invalid email address.")
            elif not is_valid_phone(new_phone):
                st.error("Invalid phone number.")
            elif check_existing_user(new_username, new_email, new_phone):
                st.error("Username, email, or phone number already in use.")
            else:
                register_user(new_username, new_name, new_last_name, new_email, new_phone, new_password)

        st.button("Already have an account? Login here", key='login_redirect', on_click=go_to_login)


        # Admin login button
        if st.button("Admin Login", key='admin_login_redirect'):
            go_to_admin_login()

    elif st.session_state.page == 'login':
        st.header("Login")
        
        username = st.text_input("Username", key='login_username')
        password = st.text_input("Password", type="password", key='login_password')

        if st.button("Login", key='login_button'):
            if not (username and password):
                st.error("Username and password are required.")
            else:
                if authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"Welcome, {username}!")
                    go_to_main()
                else:
                    st.error("Invalid username or password")

        st.button("Don't have an account? Register here", key='register_redirect', on_click=go_to_register)

        # Admin login button
        if st.button("Admin Login", key='admin_login_redirect'):
            go_to_admin_login()

    elif st.session_state.page == 'admin_login':
        st.header("Admin Login")
        
        admin_username = st.text_input("Admin Username", key='admin_username')
        admin_password = st.text_input("Admin Password", type="password", key='admin_password')

        if st.button("Login as Admin", key='admin_login_button'):
            if not (admin_username and admin_password):
                st.error("Username and password are required.")
            else:
                if is_admin(admin_username, admin_password):
                    st.session_state.admin_authenticated = True
                    go_to_admin_panel()
                else:
                    st.error("Invalid admin username or password")

        st.button("Back to Login", key='back_to_login', on_click=go_to_login)

    

    elif st.session_state.page == 'main':
        if not st.session_state.authenticated:
            st.warning("You need to be logged in to access this page.")
            go_to_login()


        # Apply theme directly using conditional layout
        theme = st.session_state.get('theme', 'light')
        st.write(f"<style>body {{background-color: {'#333' if theme == 'dark' else '#fff'}; color: {'#eee' if theme == 'dark' else '#000'};}}</style>", unsafe_allow_html=True)

        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(":bar_chart: Dynamic Data Analysis Dashboard")
            st.title(f"Welcome, {st.session_state.username}!")

        with col2:
            st.write("<div style='text-align: right;'>", unsafe_allow_html=True)
            if st.button("Edit Profile", key='edit_profile_button'):
                go_to_edit_profile()
            st.write("</div>", unsafe_allow_html=True)

            st.write("<div style='text-align: right;'>", unsafe_allow_html=True)
            if st.button("Logout", key='logout_button'):
                logout()
            st.write("</div>", unsafe_allow_html=True)
            


        # Sidebar for file upload
        uploaded_file = st.sidebar.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

        # Initialize df to None
        df = None
        # Function to read file
        def read_file(file):
            try:
                # Check the file extension
                file_extension = os.path.splitext(file.name)[1].lower()
                st.write(f"Uploaded file extension: {file_extension}")  # Debugging line
                
                if file_extension == ".csv":
                    encoding = detect_encoding(file)
                    df = pd.read_csv(file, encoding=encoding)
                
                elif file_extension in [".xls", ".xlsx"]:
                    df = pd.read_excel(file, engine='openpyxl')  # Ensure you have 'openpyxl' installed
                
                else:
                    st.error("Unsupported file type. Please upload a CSV or Excel file.")
                    return None
                
                return df
            
            except pd.errors.ParserError:
                st.error("Error parsing the file. Please check the file format.")
                return None
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return None
    
        # If a file is uploaded, read the data
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            df = read_file(uploaded_file)

        if df is not None and not df.empty:
            st.write("### Data Preview", df.head())

            # Proceed with data analysis
            numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
            
            if len(numeric_columns) > 0:
                # Calculate correlation matrix
                correlation_matrix = df[numeric_columns].corr()
                
                # Generate heatmap
                fig_heatmap = px.imshow(correlation_matrix, 
                                        title='Heatmap of Correlation Matrix',
                                        color_continuous_scale='Viridis')
                st.plotly_chart(fig_heatmap)
            else:
                st.error("No numeric columns found in the dataset to generate a heatmap.")
            
            st.sidebar.subheader("Options")
            show_data_dimensions = st.sidebar.checkbox("Show Data Dimensions", key='show_data_dimensions')
            show_field_descriptions = st.sidebar.checkbox("Show Field Descriptions", key='show_field_descriptions')
            show_summary_statistics = st.sidebar.checkbox("Show Summary Statistics", key='show_summary_statistics')
            show_value_counts = st.sidebar.checkbox("Show Value Counts of Fields", key='show_value_counts')

            # Drop-down menu for selecting plot type
            plot_type = st.sidebar.selectbox("Select plot type", ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart"])

            # Drop-down menus for selecting columns
            columns = df.columns.tolist()
            

            if show_data_dimensions:
                st.write(f"Data Dimensions: {df.shape}")

            if show_field_descriptions:
                st.write("Field Descriptions:")
                for col in df.columns:
                    st.write(f"- **{col}**: {df[col].dtype}")

            if show_summary_statistics:
                st.write("Summary Statistics:")
                st.write(df.describe())

            if show_value_counts:
                st.write("Value Counts of Fields:")
                for col in df.columns:
                    st.write(f"**{col}**:")
                    st.write(df[col].value_counts())
            
            if len(columns) > 0:
                x_col = st.sidebar.selectbox("Select X-axis column", columns)
                y_col = st.sidebar.selectbox("Select Y-axis column", columns)

                if plot_type == "Bar Chart":
                    fig = px.bar(df, x=x_col, y=y_col, title='Bar Chart')
                elif plot_type == "Line Chart":
                    fig = px.line(df, x=x_col, y=y_col, title='Line Chart')
                elif plot_type == "Scatter Plot":
                    fig = px.scatter(df, x=x_col, y=y_col, title='Scatter Plot')
                elif plot_type == "Pie Chart":
                    if df[x_col].dtype == 'object' and df[y_col].dtype in ['int64', 'float64']:
                        fig = px.pie(df, names=x_col, values=y_col, title='Pie Chart')
                    else:
                        st.error("Pie chart requires categorical. data for 'names' and numerical data for 'values'.")
                        fig = None

                if fig:
                    st.plotly_chart(fig)
            else:
                st.error("No columns found in the dataset.")
        
            
        else:
            st.write("Upload a file to start the analysis.")

    elif st.session_state.page == 'edit_profile':
        if not st.session_state.authenticated:
            st.warning("You need to be logged in to access this page.")
            go_to_login()

        st.header("Edit Profile")

        current_user = st.session_state.username

        connection = create_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    sql = "SELECT * FROM users WHERE username = %s"
                    cursor.execute(sql, (current_user,))
                    user = cursor.fetchone()
                    if user:
                        
                        first_name = st.text_input("First Name", value=user['first_name'], key='edit_first_name')
                        last_name = st.text_input("Last Name", value=user['last_name'], key='edit_last_name')
                        email = st.text_input("Email", value=user['email'], key='edit_email')
                        phone = st.text_input("Phone", value=user['phone_number'], key='edit_phone')
                        password = st.text_input("New Password", type="password", key='edit_password')
                        confirm_password = st.text_input("Confirm Password", type="password", key='edit_confirm_password')

                        if st.button("Save Changes", key='save_changes_button'):
                            if password and password != confirm_password:
                                st.error("Passwords do not match.")
                            else:
                                update_user(current_user, first_name, last_name, email, phone, password)
                    else:
                        st.error("USer not found.")
            except pymysql.MySQLError as e:
                st.error(f"Database Error: {e}")
            finally:
                connection.close()

        st.button("Back to Dashboard", key='back_to_dashboard', on_click=go_to_main)

    elif st.session_state.page == 'admin_panel':
        if not st.session_state.admin_authenticated:
            st.warning("You need to be logged in as an admin to access this page.")
            go_to_admin_login()

        st.header("Admin Panel")
        
        # Display all users
        users = get_all_users()
        if users:
            st.write("### User List")
            user_df = pd.DataFrame(users)
            st.dataframe(user_df)

            # User selection for editing
            selected_username = st.selectbox("Select a user to edit", user_df['username'].tolist())
            
            # Display selected user details
            selected_user = user_df[user_df['username'] == selected_username].iloc[0]
            first_name = st.text_input("First Name", value=selected_user['first_name'])
            last_name = st.text_input("Last Name", value=selected_user['last_name'])
            email = st.text_input("Email", value=selected_user['email'])
            phone = st.text_input("Phone", value=selected_user['phone_number'])
            new_password = st.text_input("New Password (leave blank to keep current)", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")

            if st.button("Update User"):
                if new_password and new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    update_user(selected_username, first_name, last_name, email, phone, new_password)

            
            # Delete User button
            if st.button("Delete User"):
                st.session_state.confirm_delete = True  # Set confirmation flag

            # Confirmation message for deletion
            if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
                st.warning(f"Are you sure you want to delete the user '{selected_username}'? This action cannot be undone.")
                if st.button("Yes, delete user"):
                    delete_user(selected_username)
                    st.session_state.confirm_delete = False  # Reset confirmation flag
                    st.experimental_rerun()  # Refresh the page to update the user list
                if st.button("No, cancel"):
                    st.session_state.confirm_delete = False  # Reset confirmatio

            if st.button("Logout", key='admin_logout_button'):
                logout()


    
    
except Exception as e:
    st.error(f"An error occurred: {e}")
    traceback.print_exc()

"""Message constants for flash messages and user notifications."""

# Authentication messages
AUTH_USERNAME_PASSWORD_REQUIRED = "Username and password are required."
AUTH_USER_NOT_FOUND = "User not found."
AUTH_PASSWORDS_DO_NOT_MATCH = "Passwords do not match."
AUTH_INVALID_CREDENTIALS = "Invalid username or password."
AUTH_NEW_PASSWORD_REQUIRED = "New password is required."
AUTH_LOGIN_REQUIRED = "Please log in to access this page."
AUTH_ADMIN_REQUIRED = "Admin access required."


# User management messages
USER_CREATED = "User '{username}' created successfully!"
USER_ALREADY_EXISTS = "Username already exists."
USER_PASSWORD_CHANGED = "Password for '{username}' changed successfully!"
USER_ENABLED = "User '{username}' has been enabled."
USER_DISABLED = "User '{username}' has been disabled."
USER_DELETED = "User '{username}' deleted successfully!"
USER_CANNOT_DISABLE_SELF = "You cannot disable yourself."
USER_CANNOT_DELETE_SELF = "You cannot delete yourself."
USER_TOKEN_REGENERATED = "API token regenerated for '{username}'."


# SMS messages
SMS_ENQUIRY_REQUIRED = "Enquiry Number is required."
SMS_ENQUIRY_INVALID = "Invalid Enquiry Number format. Must be in format: 4 digits, optional space, 4 digits (e.g., 1234 5678 or 12345678)."
SMS_CONTENT_REQUIRED = "Message content is required."
SMS_PHONE_INVALID = "Invalid phone number format: {invalid_numbers}. Each number must be in format: +852 followed by 8 digits (e.g., +85212345678)."
